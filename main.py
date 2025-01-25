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
db = client.gente
tareas_collection = db.tareas
colaboradores_collection = db.colaboradores


@app.route('/', methods=['GET'])
def index():
    return render_template('menu.html')

@app.route('/tareas', methods=['GET'])
def showTareas():
    tareas = list(tareas_collection.find())
    return render_template('tasks.html', tasks=tareas)

@app.route('/tareas/new', methods=['GET', 'POST'])
def newTarea():
    if request.method == 'GET':
        return render_template('new_tarea.html')
    else:
        task = {
            'responsable': request.form['inputResponsable'],
            'descripcion': request.form['inputDescripcion'],
            'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
            'segmentos': request.form['inputSegmentos'],
        }
        tareas_collection.insert_one(task)
        return redirect(url_for('showTareas'))
    
@app.route('/tareas/edit/<_id>', methods=['GET', 'POST'])
def editTarea(_id):
    if request.method == 'GET':
        tarea = tareas_collection.find_one({'_id': ObjectId(_id)})
        return render_template('edit_tarea.html', tarea=tarea)
    else:
        tarea = {
            'responsable': request.form['inputResponsable'],
            'descripcion': request.form['inputDescripcion'],
            'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
            'segmentos': request.form['inputSegmentos'],
        }
        tareas_collection.update_one({'_id': ObjectId(_id)}, {'$set': tarea})
        return redirect(url_for('showTareas'))

@app.route('/tareas/delete/<_id>', methods=['GET'])
def deleteTarea(_id):
    tareas_collection.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('showTareas'))

# CRUD de Colaboradores
@app.route('/colaboradores', methods=['GET'])
def showColaboradores():
    colaboradores = list(colaboradores_collection.find())
    return render_template('colaboradores.html', colaboradores=colaboradores)

@app.route('/colaboradores/new', methods=['GET', 'POST'])
def newColaborador():
    if request.method == 'GET':
        return render_template('new_colaborador.html')
    else:
        colaborador = {
            'email': request.form['inputEmail'],
            'nombre': request.form['inputNombre'],
            'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
        }
        colaboradores_collection.insert_one(colaborador)
        return redirect(url_for('showColaboradores'))

@app.route('/colaboradores/edit/<_id>', methods=['GET', 'POST'])
def editColaborador(_id):
    if request.method == 'GET':
        colaborador = colaboradores_collection.find_one({'_id': ObjectId(_id)})
        return render_template('edit_colaborador.html', colaborador=colaborador)
    else:
        colaborador = {
            'email': request.form['inputEmail'],
            'nombre': request.form['inputNombre'],
            'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
        }
        colaboradores_collection.update_one({'_id': ObjectId(_id)}, {'$set': colaborador})
        return redirect(url_for('showColaboradores'))

@app.route('/colaboradores/delete/<_id>', methods=['GET'])
def deleteColaborador(_id):
    colaboradores_collection.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('showColaboradores'))

@app.route('/colaboradores/<_id>/habilidades', methods=['GET'])
def getHabilidades(_id):
    colaborador = colaboradores_collection.find_one({'_id': ObjectId(_id)})
    if colaborador:
        return {'habilidades': colaborador.get('habilidades', [])}
    else:
        return {'error': 'Colaborador no encontrado'}, 404

@app.route('/colaboradores/<_id>/habilidades', methods=['POST'])
def addHabilidad(_id):
    habilidad = request.form['habilidad']
    colaboradores_collection.update_one(
        {'_id': ObjectId(_id)},
        {'$addToSet': {'habilidades': habilidad}}
    )
    return redirect(url_for('editColaborador', _id=_id))

@app.route('/colaboradores/<_id>/habilidades', methods=['POST'])
def deleteHabilidad(_id):
    if request.form.get('_method') == 'DELETE':
        habilidad = request.form['habilidad']
        colaboradores_collection.update_one(
            {'_id': ObjectId(_id)},
            {'$pull': {'habilidades': habilidad}}
        )
    else:
        habilidad = request.form['habilidad']
        colaboradores_collection.update_one(
            {'_id': ObjectId(_id)},
            {'$addToSet': {'habilidades': habilidad}}
        )
    return redirect(url_for('editColaborador', _id=_id))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)