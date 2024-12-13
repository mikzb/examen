import pymongo
from environs import Env
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import requests
from math import radians, cos, sin, sqrt, atan2
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta

app = Flask(__name__)

env = Env()
env.read_env()  # read .env file, if it exists

app.secret_key = env('GOOGLE_CLIENT_SECRET')  # Replace with your own secret key

uri = env('MONGO_URI')  # MongoDB URI from environment variable
google_client_id = env('GOOGLE_CLIENT_ID')
google_client_secret = env('GOOGLE_CLIENT_SECRET')

# OAuth configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=google_client_id,
    client_secret=google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'},
)

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id_, name, email, profile_pic):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id):
        user = users_collection.find_one({"_id": user_id})
        if not user:
            return None
        return User(user["_id"], user["name"], user["email"], user["profile_pic"])

    @staticmethod
    def create(id_, name, email, profile_pic):
        user = {
            "_id": id_,
            "name": name,
            "email": email,
            "profile_pic": profile_pic,
        }
        users_collection.insert_one(user)
        return User(id_, name, email, profile_pic)

client = pymongo.MongoClient(uri)
db = client.mimapa
users_collection = db.users
markers_collection = db.markers

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v1/userinfo')
    user_info = resp.json()
    user = User.get(user_info['id'])
    if not user:
        user = User.create(user_info['id'], user_info['name'], user_info['email'], user_info['picture'])
    login_user(user)
    
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

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
                print(lat, lon)
                return render_template('index.html', events=nearby_events, address=address, lat=lat, lon=lon)
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
@login_required
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
                'organizer': current_user.email,
                'image': request.form['inputImage']
            }
            events_collection.insert_one(event)
            return redirect(url_for('showEvents'))
        else:
            return render_template('new_event.html', error="Place not found")

@app.route('/events/edit/<_id>', methods=['GET', 'POST'])
@login_required
def editEvent(_id):
    event = events_collection.find_one({'_id': ObjectId(_id)})
    if event['organizer'] != current_user.email:
        return "You are not authorized to edit this event", 403

    if request.method == 'GET':
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
                'organizer': current_user.email,  # Ensure the organizer is the current user
                'image': request.form['inputImage']
            }
            events_collection.update_one({'_id': ObjectId(_id)}, {'$set': event})
            return redirect(url_for('showEvents'))
        else:
            return render_template('edit_event.html', event=event, error="Place not found")

@app.route('/events/delete/<_id>', methods=['GET'])
@login_required
def deleteEvent(_id):
    event = events_collection.find_one({'_id': ObjectId(_id)})
    if event['organizer'] != current_user.email:
        return "You are not authorized to delete this event", 403

    events_collection.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('showEvents'))

@app.route('/logs', methods=['GET'])
@login_required
def showLogs():
    logs = list(logs_collection.find().sort('timestamp', pymongo.DESCENDING))
    return render_template('logs.html', logs=logs)

@app.route('/add_marker', methods=['POST'])
@login_required
def add_marker():
    address = request.form['new_address']
    headers = {
        'User-Agent': 'EventualApp/1.0 (mikolajzabski@uma.es)'
    }
    response = requests.get(f'https://nominatim.openstreetmap.org/search?q={address}&format=json', headers=headers)
    if response.status_code == 200 and response.json():
        location = response.json()[0]
        lat = float(location['lat'])
        lon = float(location['lon'])
        marker = {
            'address': address,
            'lat': lat,
            'lon': lon,
            'user_id': current_user.id
        }
        markers_collection.insert_one(marker)
        return redirect(url_for('index'))
    else:
        return "Error: Could not find location", 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)