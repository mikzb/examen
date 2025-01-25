import pymongo
from environs import Env
from bson import ObjectId
from flask import Flask, request, redirect, url_for, jsonify
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
    return jsonify({'message': 'Welcome to the API'})


@app.route('/tareas', methods=['GET'])
def showTareas():
    tareas = list(tareas_collection.find())
    for tarea in tareas:
        if 'colaboradores' in tarea:
            tarea['colaboradores_nombres'] = []
            for colaborador_id in tarea['colaboradores']:
                colaborador = colaboradores_collection.find_one({'_id': ObjectId(colaborador_id)})
                if colaborador:
                    tarea['colaboradores_nombres'].append(colaborador['nombre'])
    return jsonify(tareas)


@app.route('/tareas/new', methods=['POST'])
def newTarea():
    task = {
        'responsable': request.form['inputResponsable'],
        'descripcion': request.form['inputDescripcion'],
        'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
        'segmentos': request.form['inputSegmentos'],
    }
    tareas_collection.insert_one(task)
    return jsonify({'message': 'Task created successfully'}), 201


@app.route('/tareas/edit/<_id>', methods=['POST'])
def editTarea(_id):
    tarea = {
        'responsable': request.form['inputResponsable'],
        'descripcion': request.form['inputDescripcion'],
        'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
        'segmentos': request.form['inputSegmentos'],
    }
    tareas_collection.update_one({'_id': ObjectId(_id)}, {'$set': tarea})
    return jsonify({'message': 'Task updated successfully'})


@app.route('/tareas/delete/<_id>', methods=['DELETE'])
def deleteTarea(_id):
    tareas_collection.delete_one({'_id': ObjectId(_id)})
    return jsonify({'message': 'Task deleted successfully'})


# CRUD de Colaboradores
@app.route('/colaboradores', methods=['GET'])
def showColaboradores():
    colaboradores = list(colaboradores_collection.find())
    return jsonify(colaboradores)


@app.route('/colaboradores/new', methods=['POST'])
def newColaborador():
    colaborador = {
        'email': request.form['inputEmail'],
        'nombre': request.form['inputNombre'],
        'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
    }
    colaboradores_collection.insert_one(colaborador)
    return jsonify({'message': 'Collaborator created successfully'}), 201


@app.route('/colaboradores/edit/<_id>', methods=['POST'])
def editColaborador(_id):
    colaborador = {
        'email': request.form['inputEmail'],
        'nombre': request.form['inputNombre'],
        'habilidades': request.form['inputHabilidades'].split(','),  # Split habilidades into a list
    }
    colaboradores_collection.update_one({'_id': ObjectId(_id)}, {'$set': colaborador})
    return jsonify({'message': 'Collaborator updated successfully'})


@app.route('/colaboradores/delete/<_id>', methods=['DELETE'])
def deleteColaborador(_id):
    colaboradores_collection.delete_one({'_id': ObjectId(_id)})
    return jsonify({'message': 'Collaborator deleted successfully'})


@app.route('/colaboradores/<_id>/habilidades', methods=['GET'])
def getHabilidades(_id):
    colaborador = colaboradores_collection.find_one({'_id': ObjectId(_id)})
    if colaborador:
        return jsonify({'habilidades': colaborador.get('habilidades', [])})
    else:
        return jsonify({'error': 'Colaborador no encontrado'}), 404


@app.route('/colaboradores/<_id>/habilidades/add', methods=['POST'])
def addHabilidad(_id):
    habilidad = request.form['habilidad']
    colaboradores_collection.update_one(
        {'_id': ObjectId(_id)},
        {'$addToSet': {'habilidades': habilidad}}
    )
    return jsonify({'message': 'Habilidad added successfully'})


@app.route('/colaboradores/<_id>/habilidades/delete', methods=['POST'])
def deleteHabilidad(_id):
    if request.form.get('_method') == 'DELETE':
        habilidad = request.form['habilidad']
        colaboradores_collection.update_one(
            {'_id': ObjectId(_id)},
            {'$pull': {'habilidades': habilidad}}
        )
        return jsonify({'message': 'Habilidad deleted successfully'})
    else:
        habilidad = request.form['habilidad']
        colaboradores_collection.update_one(
            {'_id': ObjectId(_id)},
            {'$addToSet': {'habilidades': habilidad}}
        )
        return jsonify({'message': 'Habilidad added successfully'})


@app.route('/tareas/habilidad/<habilidad>', methods=['GET'])
def getTareasByHabilidad(habilidad):
    tareas = list(tareas_collection.find({'habilidades': habilidad}))
    return jsonify(tareas)


@app.route('/tareas/colaborador/<_id>', methods=['GET'])
def getTareasByColaborador(_id):
    colaborador = colaboradores_collection.find_one({'_id': ObjectId(_id)})
    if colaborador:
        tareas = list(tareas_collection.find({'colaboradores': ObjectId(_id)}))
        return jsonify(tareas)
    else:
        return jsonify({'error': 'Colaborador no encontrado'}), 404


@app.route('/tareas/asignar/<_id>', methods=['POST'])
def asignarColaborador(_id):
    colaborador_id = request.form['colaborador_id']
    colaborador = colaboradores_collection.find_one({'_id': ObjectId(colaborador_id)})
    tarea = tareas_collection.find_one({'_id': ObjectId(_id)})

    if not colaborador or not tarea:
        return jsonify({'error': 'Colaborador o tarea no encontrado'}), 404

    # Check if the collaborator has at least one of the required skills
    if not any(habilidad in colaborador['habilidades'] for habilidad in tarea['habilidades']):
        return jsonify({'error': 'El colaborador no posee ninguna de las habilidades requeridas'}), 400

    # Assign the collaborator to the task
    tareas_collection.update_one(
        {'_id': ObjectId(_id)},
        {'$addToSet': {'colaboradores': ObjectId(colaborador_id)}}
    )
    return jsonify({'message': 'Colaborador assigned to task successfully'})


@app.route('/tareas/<_id>/candidatos', methods=['POST'])
def getCandidatos(_id):
    tarea = tareas_collection.find_one({'_id': ObjectId(_id)})
    colaboradores = list(colaboradores_collection.find())
    candidatos = []
    for colaborador in colaboradores:
        if any(habilidad in colaborador['habilidades'] for habilidad in tarea['habilidades']):
            candidatos.append(colaborador)
    return jsonify({'candidatos': candidatos, 'tarea': tarea})


@app.route('/colaboradores/responsable/<responsable_email>', methods=['GET'])
def getColaboradoresByResponsable(responsable_email):
    # Find tasks for which the user is responsible
    tareas = list(tareas_collection.find({'responsable': responsable_email}))

    # Collect the emails of collaborators assigned to those tasks
    colaborador_ids = set()
    for tarea in tareas:
        if 'colaboradores' in tarea:
            colaborador_ids.update(tarea['colaboradores'])

    # Find the collaborators by their IDs
    colaboradores = colaboradores_collection.find({'_id': {'$in': list(colaborador_ids)}})

    # Collect the emails of the collaborators
    emails = [colaborador['email'] for colaborador in colaboradores]

    return jsonify({'emails': emails})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)