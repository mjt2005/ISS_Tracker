# ISS Tracker
## Overview:
The following folder contains a python script, iss_tracker_app.py, for tracking the geolocation and instantaneous speed of the International Space Station (ISS) based on NASA public data. To accompany the python script, there is a corresponding pytest script used to test the Flask routes used in iss_tracker_app.py. The primary objective of this project was to demonstrate the practice of containerizing Flask and Redis applications, so each function written to analyze the ISS data is accessible via a Flask route and queries data from a Redis datavase. This will be explained in further detail below.
## Descriptions and Instructions:
1. Locate the data used for this project at [data](https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml). Note that this data includes the ephemeris of the ISS every 4 minutes for a total of 15 days, so the data will change based on when you retrieve it. The data is in XML format and primarily contains infomation on the position and velocity of the ISS. There is no need to download the data since it is hardcoded to be fetched from the url in my program.
2. Since we will be storing back-up data locally, you will need to create a /data folder in your current directory by typing the command ```mkdir data```.
3. Because the entire program is containerized, all you need to do to gain access to it is pull my public image from Dockerhub with the command ```docker pull mjt2005/iss_tracker_app:2.0```. Before we go any further, ensure that you have nothing running on port 5000 by running the command ```lsof -i :5000``` which should return nothing if it is free.
4. Once my image is in your working directory, you can build it by typing the command ```docker compose build``` and then run it in the background with ```docker compose up -d```. While you will not be able to navigate around the container, that is not neccessary since we will be using Flask routes to run my programs.
5. Upon starting, my program will fetch the ISS data from the NASA website and store it in a Redis database. If you exit the program and come back to it, it will not re-fetch the data because it has persisted in Redis.
6. To access my functions:

| Command | Inputs | Output |
|---------|--------|--------|
| ```curl localhost:5000/epochs``` | None | All epochs in the dataset, formatted in XML |
| ```curl 'localhost:5000/epochs_query?limit=<start>&<last>'``` | 'start' & 'last' - Day of the year bounds for the range of data requested | A subset of the dataset |
| ```curl localhost:5000/epochs/<epoch>``` | 'epoch' - The epoch you wish to see, formatted as it is in the raw data | The state vectors for the epoch |
| ```curl localhost:5000/epochs/<epoch>/speed``` | 'epoch' - The epoch you wish to see, formatted as it is in the raw data | The instantaneous speed in km/s of the ISS at that epoch |
| ```curl localhost:5000/now``` | None | The current epoch, latitude, longitude, altitude, and geolocation of the ISS |
| ```curl localhost:5000/epochs/<epoch>/location``` | The epoch you wish to see, formatted as it is in the raw data | The latitude, longitude, altitude, and geolocation of the ISS at that epoch |
5. Note that the program will alert you if the epoch entered is not in the correct format (correct ex: '2025-060T05:49:00.000Z') or if the epoch entered is not in the current ephemeris (ex: something from 2024). Also, since the timestamp for each epoch in the data is formatted where the day represents the absolute day of the year (ex: February 1st is 32), by 'day of the year bounds' I mean the first and last days you wish to retrive data for. For example, start= 80 and last = 85 will give data for the 80th through 85th day of 2025. Remember that the data only contains information over a 15-day period.
6. To run my pytests, simply type the command ```pytest``` in your working directory. All tests should pass

## Software Diagram
- The following software diagram demonstrates how Docker strings together Flask and Redis to connect the data for use in web routes.
![diagram](./ml_data_diagram1.jpg)

## Use of AI/ Outside Resources:
AI was used for the following lines in iss_app.py:
1. current_time = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
- I used ChatGPT to help debug an error where 2 datetime objects could not be subtracted because one was time-zone naive and the other was not. Because I hard-coded everything to be in UTC time, ChatGPT produced the last argument in the .replace() function to get rid of time zone info. I also used ChatGPT to produce the test_closest_to_now function because I felt it would take too long to do my hand, and I could not think of a good unit test for that function.
2. pattern = r'^\d{4}-\d{3}T\d{2}:\d{2}:\d{2}\.\d{3}Z$' 
   if not re.match(pattern,epoch): 
- I used ChatGPT to generate this line because I am not familar with the re library and it would have been tedious to write this by hand.
3. response_data = {
        "closest_epoch": closest_epoch,
        "speed": speed
    }
    return Response(json.dumps(response_data), status=200, mimetype="application/json")
- I used ChatGPT for this because I could not figure out how to return both a dictionary and a string in the route.
4. regex_pattern = rf'2025-(0{start}|[5-9]\d|{start+1:02d}|{last:03d})T\d{{2}}:\d{{2}}:\d{{2}}\.\d{{3}}Z'
    ...
    valid_keys = [key.decode() for key in keys if re.fullmatch(regex_pattern, key.decode())] 
    - I used ChatGPT for these lines because again, I am not familiar with the re library and I did not know how to populate a list of keys that matched the pattern.