import pymongo

from environs import Env
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime


app = Flask(__name__)

env = Env()
env.read_env()  # read .env file, if it exists

uri = env('MONGO_URI')              # establecer la variable de entorno MONGO_URI con la URI de la base de datos
                                    # MongoDB local:
                                    #     MONGO_URI = mongodb://localhost:27017
                                    # MongoDB Atlas:
                                    #     MONGO_URI = mongodb+srv://<USER>:<PASS>@<CLUSTER>.mongodb.net/?retryWrites=true&w=majority
                                    # MongoDB en Docker
                                    #     MONGO_URI = mongodb://root:example@mongodb:27017

print("MONGO_URI: ",uri)

client = pymongo.MongoClient(uri)

db = client.misAnuncios   # db = client['misAnuncios']

ads = db.ads              # ads = db['ads']

# Definicion de metodos para endpoints

@app.route('/', methods=['GET'])
def showAds():
    
    return render_template('ads.html', ads = list(ads.find().sort('date',pymongo.DESCENDING)))
    
@app.route('/new', methods = ['GET', 'POST'])
def newAd():

    if request.method == 'GET' :
        return render_template('new.html')
    else:
        ad = {'author': request.form['inputAuthor'],
              'text': request.form['inputText'], 
              'priority': int(request.form['inputPriority']),
              'date': datetime.now()
             }
        ads.insert_one(ad)
        return redirect(url_for('showAds'))

@app.route('/edit/<_id>', methods = ['GET', 'POST'])
def editAd(_id):
    
    if request.method == 'GET' :
        ad = ads.find_one({'_id': ObjectId(_id)})
        return render_template('edit.html', ad = ad)
    else:
        ad = { 'author': request.form['inputAuthor'],
               'text': request.form['inputText'],
               'priority' : int(request.form['inputPriority'])
             }
        ads.update_one({'_id': ObjectId(_id) }, { '$set': ad })    
        return redirect(url_for('showAds'))

@app.route('/delete/<_id>', methods = ['GET'])
def deleteAd(_id):
    
    ads.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('showAds'))

if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App Engine
    # or Heroku, a webserver process such as Gunicorn will serve the app. In App
    # Engine, this can be configured by adding an `entrypoint` to app.yaml.
    app.run(host='127.0.0.1', port=8000, debug=True)

    # ejecucion en local: python main.py
