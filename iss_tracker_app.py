from flask import Flask, request, Response
import redis
import logging
import requests
import xmltodict
import numpy as np
from datetime import datetime, timezone
import json
import re
import time
from astropy import coordinates
from astropy import units
from astropy.time import Time
from geopy.geocoders import Nominatim
from geolocation import compute_location

logging.basicConfig(level='DEBUG')

def get_redis_client():
    return redis.Redis(host='redis-db', port=6379, db=0)

rd = get_redis_client()

# save data for use in later functions

if not rd.keys():
    dat = requests.get('https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml').text 
    logging.info('Successfully fetched data from url')
    xml_data = xmltodict.parse(dat) # convert to proper dictionary xml format
    try:
        stateVectors = xml_data['ndm']['oem']['body']['segment']['data']['stateVector'] # roots to access the ephemeris
    except KeyError as k:
        logging.error(f'Root names of xml data are different: {k}')
    for i in stateVectors:
        try:
            rd.set(i['EPOCH'], json.dumps(i))
        except Exception:
            logging.error(f'Error pushing data to redis, {i}')


app = Flask(__name__)

@app.route('/epochs', methods = ['GET'])
def return_data() -> dict:
    '''
        This function returns the statevectors from the dataset
        Args:
            None
        Returns:
            data (dict of JSON): the epochs of the ISS data 
    '''
    # initialize data dictionary
    data = {}
    # loop thru Redis keys
    for key in rd.keys('*'):
        key = key.decode('utf-8')
        val = json.loads(rd.get(key).decode('utf-8')) # get value of key
        data[key] = val # add key value pair to data dictionary
    
    return data

@app.route('/epochs/<epoch>', methods = ['GET'])
def find_epoch(epoch : str) -> list:
    '''
        This function returns a specific epoch from the dataset
        Args:
            epoch: an epoch (timestamp)
        Returns:
            i (list of dicts): the full epoch given
    '''
    pattern = r'^\d{4}-\d{3}T\d{2}:\d{2}:\d{2}\.\d{3}Z$' # epoch format (used ChatGPT to generate)
    if not re.match(pattern,epoch): # error if epoch not in correct format
        return 'Invalid epoch entered'
    try:
        return json.loads(rd.get(epoch).decode('utf-8')) 
    except AttributeError:
        logging.warning('Epoch is not contained in the current ephemeris')
        return 'Epoch is not contained in the current ephemeris'

@app.route('/epochs/<epoch>/speed', methods= ['GET'])
def get_speed(epoch : str) -> str:
    '''
        This function returns the speed of a given epoch
        Args:
            epoch (str): an epoch (timestamp)
        Returns:
            speed (str): instantaneous speed of the ISS
    '''
    pattern = r'^\d{4}-\d{3}T\d{2}:\d{2}:\d{2}\.\d{3}Z$' # epoch format
    if not re.match(pattern,epoch):
        return 'invalid epoch entered' # graceful error if epoch in wrong format
    try:
        spec = json.loads(rd.get(epoch).decode('utf-8')) # get specific epoch from redis
    except AttributeError:
        logging.warning('Epoch is not contained in the current ephemeris\n')
        return ('Epoch is not contained in the current ephemeris\n')

    # extract velocities
    try:
        x_dot = float(spec['X_DOT'].get('#text'))
        y_dot = float(spec['Y_DOT'].get('#text'))
        z_dot = float(spec['Z_DOT'].get('#text'))
        speed = np.sqrt((x_dot)**2 + (y_dot)**2 + (z_dot)**2) # calculate speed
        logging.info('successfully calculated instantaneous speed')
    except Exception:
        logging.debug(f"missing velocity value at {spec['EPOCH']}")
    return str(speed) + ' km/s' 

@app.route('/now', methods= ['GET'])
def closest_to_now() -> dict:
    '''
    This function finds the time, position, velocity, and instantaneous speed of the ISS station closest to 'now'
    Args:
        None
    Returns:
        Response (dict): dict containing the full epoch closest to now as the first key value pair, the instantaneous speed as the second, and the geolocation of the ISS as the third
    '''
    current_time = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None) # finds current time at runtime, AI was used for this
    samp_time = (datetime.strptime(rd.keys('*')[0].decode(),"%Y-%jT%H:%M:%S.%fZ")) # use first epoch in Redis as sample time
    closest_time = abs(samp_time - current_time) # initialize smallest time diff
    # loop thru redis keys (timestamps)
    for k in rd.keys('*'):
        k = k.decode('utf-8')
        dt = datetime.strptime(k, "%Y-%jT%H:%M:%S.%fZ")
        time_diff = abs(dt - current_time)
        if time_diff < closest_time: # if time difference less than closest time diff, time diff becomes new closest time
            closest_time = time_diff
            logging.info('Calculating closest epoch...')
            closest_epoch = json.loads(rd.get(k).decode('utf-8')) # closest whole epoch
    # get velocities of closest epoch
    try:
        x_dot = float(closest_epoch['X_DOT'].get('#text'))
        y_dot = float(closest_epoch['Y_DOT'].get('#text'))
        z_dot = float(closest_epoch['Z_DOT'].get('#text'))
        speed = np.sqrt((x_dot)**2 + (y_dot)**2 + (z_dot)**2) # calculate speed
        logging.info('successfully calculated instantaneous speed')
    except Exception as n:
        logging.debug(f"missing velocity value at {stateVectors[i]}")
    
    closest_data = compute_location(closest_epoch)

    response_data = {
        "epoch" : closest_epoch["EPOCH"],
        "speed": str(speed) + ' km/s',
        "geolocation": closest_data
        }
    return Response(json.dumps(response_data), status=200, mimetype="application/json") # used AI for this line

@app.route('/epochs_query', methods= ['GET'])
def query_iss():
    ''''
    This function returns a subset of the data based on the given range of days the user requests
    Args:
        None
    Returns:
        subdata (dict): dict of the data in the given range
    '''
    try:
        start = int(request.args.get('limit'))
    except Exception as e:
        return "Day must be numeric\n"
    try:
        last = int(request.args.get('offset'))
    except Exception:
        return "Day must be numeric\n"
    if start > last:
        return 'Starting day must be before last day\n'
    if (start > 365) or (start < 0):
        return 'Days must be [0-365]\n'
    if (last > 365) or (last < 0):
        return 'Days must be [0-365]\n'
    
    # ChatGPT produced the following lines

    # Create a regex pattern that dynamically enforces the day-of-year range
    regex_pattern = rf'2025-(0{start}|[5-9]\d|{start+1:02d}|{last:03d})T\d{{2}}:\d{{2}}:\d{{2}}\.\d{{3}}Z'

    keys = rd.keys('*') 
    valid_keys = [key.decode() for key in keys if re.fullmatch(regex_pattern, key.decode())] 
    
    subdata = {}
    for key in valid_keys: 
        val = json.loads(rd.get(key).decode('utf-8'))
        subdata[key] = val
    if subdata:
        return subdata
    else:
        logging.warning('Days entered are not contained in the current ephemeris')
        return 'Days entered are not contained in the current ephemeris\n'

@app.route('/epochs/<epoch>/location', methods= ['GET'])
def compute_location_astropy(epoch):
    
    pattern = r'^\d{4}-\d{3}T\d{2}:\d{2}:\d{2}\.\d{3}Z$' # epoch format
    if not re.match(pattern,epoch):
        return 'invalid epoch entered' # graceful error if epoch in wrong format
    try:
        spec_epoch = json.loads(rd.get(epoch).decode('utf-8')) # get specific epoch from Redis
    except AttributeError:
        logging.warning('Epoch is not contained in the current ephemeris')
        return 'Epoch is not contained in the current ephemeris\n'

    # get x,y,z locations
    x = float(spec_epoch['X'].get('#text'))
    y = float(spec_epoch['Y'].get('#text'))
    z = float(spec_epoch['Z'].get('#text'))

    # assumes epoch is in format '2024-067T08:28:00.000Z'
    this_epoch=time.strftime('%Y-%m-%d %H:%m:%S', time.strptime(spec_epoch['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))
    cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
    gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
    loc = coordinates.EarthLocation(*itrs.cartesian.xyz)
    geocoder = Nominatim(user_agent='iss_tracker')
    geoloc = geocoder.reverse((loc.lat.value,loc.lon.value), zoom=30, language='en')

    # if geolocation found, return address
    if geoloc:
        response_data = {
            'latitude' : loc.lat.value,
            'longitude' : loc.lon.value,
            'altitude' : loc.height.value,
            'geolocation' : geoloc.address
        }
    # if not, ISS geolocation could not be found or it is likely over an ocean
    else:
        response_data = {
            'latitude' : loc.lat.value,
            'longitude' : loc.lon.value,
            'altitude' : loc.height.value,
            'geolocation' : 'None found/ Ocean'
        }
    
    return Response(json.dumps(response_data), status=200, mimetype="application/json")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')