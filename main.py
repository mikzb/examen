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
import cloudinary
import cloudinary.uploader
import cloudinary.api


app = Flask(__name__)

cloudinary.config(
  cloud_name = 'da5v08x9g',
  api_key = '199397127967679',
  api_secret = 'JV694YWmyg4l09xsuW9sGMz31Ug'
)

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not authenticated


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
login_manager.login_view = 'login'

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

@app.route('/', methods=['GET', 'POST'])
@login_required
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
                return render_template('index.html', markers=markers_collection.find({'user_id': current_user.id}))
            else:
                return render_template('index.html', error="Address not found", markers=markers_collection.find({'user_id': current_user.id}))
        except requests.exceptions.JSONDecodeError:
            print("Error decoding JSON response")
            return render_template('index.html', error="Error decoding JSON response", markers=markers_collection.find({'user_id': current_user.id}))
    return render_template('index.html', markers=markers_collection.find({'user_id': current_user.id}))

@app.route('/markers/edit/<_id>', methods=['GET', 'POST'])
@login_required
def editMarker(_id):
    marker = markers_collection.find_one({'_id': ObjectId(_id), 'user_id': current_user.id})
    if not marker:
        return "Marker not found", 404

    if request.method == 'POST':
        address = request.form['new_address']
        image = request.files['image']

        # Upload the new image to Cloudinary if a new image is provided
        if image:
            result = cloudinary.uploader.upload(image)
            image_url = result['secure_url']
        else:
            image_url = marker['image_url']

        headers = {
            'User-Agent': 'EventualApp/1.0 (mikolajzabski@uma.es)'
        }
        response = requests.get(f'https://nominatim.openstreetmap.org/search?q={address}&format=json', headers=headers)
        if response.status_code == 200 and response.json():
            location = response.json()[0]
            lat = float(location['lat'])
            lon = float(location['lon'])

            # Update the marker in the database
            markers_collection.update_one(
                {'_id': ObjectId(_id)},
                {'$set': {
                    'address': address,
                    'lat': lat,
                    'lon': lon,
                    'image_url': image_url
                }}
            )
            return redirect(url_for('index'))
        else:
            return "Error: Could not find location", 400

    return render_template('edit_marker.html', marker=marker)

@app.route('/markers/delete/<_id>', methods=['GET'])
@login_required
def deleteMarker(_id):
    marker = markers_collection.find_one({'_id': ObjectId(_id), 'user_id': current_user.id})
    if not marker:
        return "Marker not found", 404

    markers_collection.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('index'))

@app.route('/logs', methods=['GET'])
@login_required
def showLogs():
    logs = list(logs_collection.find().sort('timestamp', pymongo.DESCENDING))
    return render_template('logs.html', logs=logs)

@app.route('/add_marker', methods=['POST'])
@login_required
def add_marker():
    address = request.form['new_address']
    image = request.files['image']
    
    result = cloudinary.uploader.upload(image)
    image_url = result['secure_url']

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
            'image_url': image_url,
            'user_id': current_user.id
            
        }
        markers_collection.insert_one(marker)
        return redirect(url_for('index'))
    else:
        return "Error: Could not find location", 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)