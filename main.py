import pymongo
from environs import Env
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

env = Env()
env.read_env()  # read .env file, if it exists

uri = env('MONGO_URI')  # MongoDB URI from environment variable

print("MONGO_URI: ", uri)

client = pymongo.MongoClient(uri)
db = client.eventual
events_collection = db.eventos

@app.route('/events', methods=['GET'])
def showEvents():
    events = list(events_collection.find().sort('timestamp', pymongo.DESCENDING))
    return render_template('events.html', events=events)

@app.route('/events/new', methods=['GET', 'POST'])
def newEvent():
    if request.method == 'GET':
        return render_template('new_event.html')
    else:
        event = {
            'name': request.form['inputName'],
            'timestamp': datetime.strptime(request.form['inputTimestamp'], '%Y-%m-%dT%H:%M'),
            'place': request.form['inputPlace'],
            'lat': float(request.form['inputLat']),
            'lon': float(request.form['inputLon']),
            'organizer': request.form['inputOrganizer'],
            'image': request.form['inputImage']
        }
        events_collection.insert_one(event)
        return redirect(url_for('showEvents'))

@app.route('/events/edit/<_id>', methods=['GET', 'POST'])
def editEvent(_id):
    if request.method == 'GET':
        event = events_collection.find_one({'_id': ObjectId(_id)})
        return render_template('edit_event.html', event=event)
    else:
        event = {
            'name': request.form['inputName'],
            'timestamp': datetime.strptime(request.form['inputTimestamp'], '%Y-%m-%dT%H:%M'),
            'place': request.form['inputPlace'],
            'lat': float(request.form['inputLat']),
            'lon': float(request.form['inputLon']),
            'organizer': request.form['inputOrganizer'],
            'image': request.form['inputImage']
        }
        events_collection.update_one({'_id': ObjectId(_id)}, {'$set': event})
        return redirect(url_for('showEvents'))

@app.route('/events/delete/<_id>', methods=['GET'])
def deleteEvent(_id):
    events_collection.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('showEvents'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)