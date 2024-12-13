import pymongo
from environs import Env
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import requests
from math import radians, cos, sin, sqrt, atan2

app = Flask(__name__)

env = Env()
env.read_env()  # read .env file, if it exists

uri = env('MONGO_URI')  # MongoDB URI from environment variable

print("MONGO_URI: ", uri)

client = pymongo.MongoClient(uri)
db = client.eventual
events_collection = db.eventos

def calculate_distance(lat1, lon1, lat2, lon2):
     # Convert latitude and longitude from degrees to radians
     lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
     # Haversine formula
     dlon = lon2 - lon1
     dlat = lat2 - lat1
     a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
     c = 2 * atan2(sqrt(a), sqrt(1 - a))
     distance = 6371 * c  # Radius of Earth in kilometers
     return distance


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        address = request.form['address']
        headers = {
            'User-Agent': 'EventualApp/1.0 (mikolajzabski@uma.es)'
        }
        response = requests.get(f'https://nominatim.openstreetmap.org/search?q={address}&format=json', headers=headers)
        try:
            response_json = response.json()
            if response.status_code == 200 and response_json:
                location = response_json[0]
                lat = float(location['lat'])
                lon = float(location['lon'])
                events = list(events_collection.find())
                nearby_events = [event for event in events if calculate_distance(lat, lon, event['lat'], event['lon']) <= 0.3]
                # print distance between address and events for debugging
                return render_template('index.html', events=nearby_events, address=address)
            else:
                return render_template('index.html', error="Address not found")
        except requests.exceptions.JSONDecodeError:
            print("Error decoding JSON response")
            return render_template('index.html', error="Error decoding JSON response")
    return render_template('index.html')

@app.route('/events', methods=['GET'])
def showEvents():
    events = list(events_collection.find().sort('timestamp', pymongo.DESCENDING))
    return render_template('events.html', events=events)

@app.route('/events/new', methods=['GET', 'POST'])
def newEvent():
    if request.method == 'GET':
        return render_template('new_event.html')
    else:
        place = request.form['inputPlace']
        headers = {
            'User-Agent': 'EventualApp/1.0 (mikolajzabski@uma.es)'
        }
        response = requests.get(f'https://nominatim.openstreetmap.org/search?q={place}&format=json', headers=headers)
        if response.status_code == 200 and response.json():
            location = response.json()[0]
            lat = float(location['lat'])
            lon = float(location['lon'])
            event = {
                'name': request.form['inputName'],
                'timestamp': datetime.strptime(request.form['inputTimestamp'], '%Y-%m-%dT%H:%M'),
                'place': place,
                'lat': lat,
                'lon': lon,
                'organizer': request.form['inputOrganizer'],
                'image': request.form['inputImage']
            }
            events_collection.insert_one(event)
            return redirect(url_for('showEvents'))
        else:
            return render_template('new_event.html', error="Place not found")

@app.route('/events/edit/<_id>', methods=['GET', 'POST'])
def editEvent(_id):
    if request.method == 'GET':
        event = events_collection.find_one({'_id': ObjectId(_id)})
        return render_template('edit_event.html', event=event)
    else:
        place = request.form['inputPlace']
        headers = {
            'User-Agent': 'EventualApp/1.0 (mikolajzabski@uma.es)'
        }
        response = requests.get(f'https://nominatim.openstreetmap.org/search?q={place}&format=json', headers=headers)
        if response.status_code == 200 and response.json():
            location = response.json()[0]
            lat = float(location['lat'])
            lon = float(location['lon'])
            event = {
                'name': request.form['inputName'],
                'timestamp': datetime.strptime(request.form['inputTimestamp'], '%Y-%m-%dT%H:%M'),
                'place': place,
                'lat': lat,
                'lon': lon,
                'organizer': request.form['inputOrganizer'],
                'image': request.form['inputImage']
            }
            events_collection.update_one({'_id': ObjectId(_id)}, {'$set': event})
            return redirect(url_for('showEvents'))
        else:
            return render_template('edit_event.html', event=event, error="Place not found")
        
# Ensure the app is callable by Vercel
app = app

@app.route('/events/delete/<_id>', methods=['GET'])
def deleteEvent(_id):
    events_collection.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('showEvents'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)