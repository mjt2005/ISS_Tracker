import numpy as np
from datetime import datetime, timezone
from astropy import coordinates
from astropy import units
from geopy.geocoders import Nominatim

def compute_location(epoch):
    print(epoch)
    x = float(epoch['X'].get('#text'))
    y = float(epoch['Y'].get('#text'))
    z = float(epoch['Z'].get('#text'))

    # assumes epoch is in format '2024-067T08:28:00.000Z'
    this_epoch=(datetime.strptime(epoch['EPOCH'],"%Y-%jT%H:%M:%S.%fZ"))

    cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
    gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
    loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

    geocoder = Nominatim(user_agent='iss_tracker')
    geoloc = geocoder.reverse((loc.lat.value, loc.lon.value), zoom=15, language='en')
    if geoloc:
        response_data = {
        "latitude": loc.lat.value,
        "longitude": loc.lon.value,
        "altitude" : loc.height.value,
        "geoloc" : geoloc.address}
    else:
        response_data = {
        "latitude": loc.lat.value,
        "longitude": loc.lon.value,
        "altitude" : loc.height.value,
        "geolocation" : 'None found/ Ocean'}
    
    return response_data