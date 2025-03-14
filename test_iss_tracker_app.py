import pytest
import requests

response1 = requests.get('http://127.0.0.1:5000/epochs')
a_representative_epoch = response1.json()
response2 = requests.get('http://127.0.0.1:5000/epochs/2025-084T11:58:30.000Z')
response3 = requests.get('http://127.0.0.1:5000/epochs/2025-084T11:58:30.000Z/speed')
response4 = requests.get('http://127.0.0.1:5000/epochs_query?limit=366&offset=400') # should not work

def test_epochs_route():
    assert response1.status_code == 200
    assert isinstance(response1.json(), dict) == True

def test_find_epoch_route():
    assert response2.status_code == 200
    assert isinstance(response2.json(), dict) == True

def test_get_speed_route():
    assert response3.status_code == 200
    assert isinstance(response3.text, str) == True

def test_query_iss_route():
    assert response4.status_code == 200
    assert isinstance(response4.text, dict) == False




