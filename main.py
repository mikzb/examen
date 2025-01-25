import pymongo
from environs import Env
from bson import ObjectId
from flask import Flask, request, jsonify

app = Flask(__name__)

env = Env()
env.read_env()  # read .env file, if it exists

uri = env('MONGO_URI')  # MongoDB URI from environment variable

print("MONGO_URI: ", uri)

client = pymongo.MongoClient(uri)
db = client.gente
tareas_collection = db.tareas
colaboradores_collection = db.colaboradores

# CRUD de tareas
@app.route('/tareas', methods=['GET'])
def get_all_tareas():
    tareas = list(tareas_collection.find())
    for tarea in tareas:
        tarea['_id'] = str(tarea['_id'])
        if 'colaboradores' in tarea:
            tarea['colaboradores'] = [str(colaborador) for colaborador in tarea['colaboradores']]
    return jsonify(tareas)

@app.route('/tareas/<id>', methods=['GET'])
def get_tarea(id):
    tarea = tareas_collection.find_one({'_id': ObjectId(id)})
    if tarea:
        tarea['_id'] = str(tarea['_id'])
        if 'colaboradores' in tarea:
            tarea['colaboradores'] = [str(colaborador) for colaborador in tarea['colaboradores']]
        return jsonify(tarea)
    return jsonify({'error': 'Tarea no encontrada'}), 404

@app.route('/tareas', methods=['POST'])
def create_tarea():
    data = request.json
    tarea_id = tareas_collection.insert_one(data).inserted_id
    return jsonify({'_id': str(tarea_id)}), 201

@app.route('/tareas/<id>', methods=['PUT'])
def update_tarea(id):
    data = request.json
    result = tareas_collection.update_one({'_id': ObjectId(id)}, {'$set': data})
    if result.matched_count:
        return jsonify({'message': 'Tarea actualizada'})
    return jsonify({'error': 'Tarea no encontrada'}), 404

@app.route('/tareas/<id>', methods=['DELETE'])
def delete_tarea(id):
    result = tareas_collection.delete_one({'_id': ObjectId(id)})
    if result.deleted_count:
        return jsonify({'message': 'Tarea eliminada'})
    return jsonify({'error': 'Tarea no encontrada'}), 404

# CRUD de colaboradores
@app.route('/colaboradores', methods=['GET'])
def get_all_colaboradores():
    colaboradores = list(colaboradores_collection.find())
    for colaborador in colaboradores:
        colaborador['_id'] = str(colaborador['_id'])
    return jsonify(colaboradores)

@app.route('/colaboradores/<id>', methods=['GET'])
def get_colaborador(id):
    colaborador = colaboradores_collection.find_one({'_id': ObjectId(id)})
    if colaborador:
        colaborador['_id'] = str(colaborador['_id'])
        return jsonify(colaborador)
    return jsonify({'error': 'Colaborador no encontrado'}), 404

@app.route('/colaboradores', methods=['POST'])
def create_colaborador():
    data = request.json
    colaborador_id = colaboradores_collection.insert_one(data).inserted_id
    return jsonify({'_id': str(colaborador_id)}), 201

@app.route('/colaboradores/<id>', methods=['DELETE'])
def delete_colaborador(id):
    result = colaboradores_collection.delete_one({'_id': ObjectId(id)})
    if result.deleted_count:
        return jsonify({'message': 'Colaborador eliminado'})
    return jsonify({'error': 'Colaborador no encontrado'}), 404

# CRUD de habilidades de un colaborador
@app.route('/colaboradores/<id>/habilidades', methods=['GET'])
def get_all_habilidades(id):
    colaborador = colaboradores_collection.find_one({'_id': ObjectId(id)}, {'habilidades': 1})
    if colaborador:
        return jsonify(colaborador.get('habilidades', []))
    return jsonify({'error': 'Colaborador no encontrado'}), 404

@app.route('/colaboradores/<id>/habilidades', methods=['POST'])
def add_habilidad(id):
    data = request.json
    habilidad = data.get('habilidad')
    if habilidad:
        result = colaboradores_collection.update_one({'_id': ObjectId(id)}, {'$addToSet': {'habilidades': habilidad}})
        if result.matched_count:
            return jsonify({'message': 'Habilidad añadida'})
    return jsonify({'error': 'Colaborador no encontrado o habilidad no proporcionada'}), 404

@app.route('/colaboradores/<id>/habilidades', methods=['DELETE'])
def delete_habilidad(id):
    data = request.json
    habilidad = data.get('habilidad')
    if habilidad:
        result = colaboradores_collection.update_one({'_id': ObjectId(id)}, {'$pull': {'habilidades': habilidad}})
        if result.matched_count:
            return jsonify({'message': 'Habilidad eliminada'})
    return jsonify({'error': 'Colaborador no encontrado o habilidad no proporcionada'}), 404

# Nuevas funcionalidades

@app.route('/tareas/habilidad/<habilidad>', methods=['GET'])
def get_tareas_by_habilidad(habilidad):
    tareas = list(tareas_collection.find({'habilidades': habilidad}))
    for tarea in tareas:
        tarea['_id'] = str(tarea['_id'])
        if 'colaboradores' in tarea:
            tarea['colaboradores'] = [str(colaborador) for colaborador in tarea['colaboradores']]
    return jsonify(tareas)

@app.route('/tareas/colaborador/<colaborador_id>', methods=['GET'])
def get_tareas_by_colaborador(colaborador_id):
    tareas = list(tareas_collection.find({'colaboradores': ObjectId(colaborador_id)}))
    for tarea in tareas:
        tarea['_id'] = str(tarea['_id'])
        if 'colaboradores' in tarea:
            tarea['colaboradores'] = [str(colaborador) for colaborador in tarea['colaboradores']]
    return jsonify(tareas)

@app.route('/tareas/<tarea_id>/asignar/<colaborador_id>', methods=['POST'])
def assign_colaborador_to_tarea(tarea_id, colaborador_id):
    tarea = tareas_collection.find_one({'_id': ObjectId(tarea_id)})
    colaborador = colaboradores_collection.find_one({'_id': ObjectId(colaborador_id)})
    if tarea and colaborador:
        if any(habilidad in colaborador.get('habilidades', []) for habilidad in tarea.get('habilidades', [])):
            result = tareas_collection.update_one({'_id': ObjectId(tarea_id)}, {'$addToSet': {'colaboradores': ObjectId(colaborador_id)}})
            if result.matched_count:
                return jsonify({'message': 'Colaborador asignado a la tarea'})
        return jsonify({'error': 'El colaborador no posee las habilidades requeridas'}), 400
    return jsonify({'error': 'Tarea o colaborador no encontrado'}), 404

@app.route('/tareas/<tarea_id>/candidatos', methods=['GET'])
def get_candidatos_for_tarea(tarea_id):
    tarea = tareas_collection.find_one({'_id': ObjectId(tarea_id)})
    if tarea:
        habilidades = tarea.get('habilidades', [])
        candidatos = colaboradores_collection.find({'habilidades': {'$in': habilidades}})
        emails = [candidato['email'] for candidato in candidatos]
        return jsonify(emails)
    return jsonify({'error': 'Tarea no encontrada'}), 404

@app.route('/tareas/completamente_asignadas', methods=['GET'])
def get_completamente_asignadas():
    pipeline = [
        {
            '$addFields': {
                'num_colaboradores': {'$size': {'$ifNull': ['$colaboradores', []]}}
            }
        },
        {
            '$match': {
                '$expr': {'$eq': ['$num_colaboradores', '$segmentos']}
            }
        }
    ]
    tareas = list(tareas_collection.aggregate(pipeline))
    for tarea in tareas:
        tarea['_id'] = str(tarea['_id'])
        if 'colaboradores' in tarea:
            tarea['colaboradores'] = [str(colaborador) for colaborador in tarea['colaboradores']]
    return jsonify(tareas)

@app.route('/colaboradores/responsable/<email>', methods=['GET'])
def get_colaboradores_by_responsable(email):
    tareas = list(tareas_collection.find({'responsable': email}))
    colaboradores_ids = set()
    for tarea in tareas:
        colaboradores_ids.update(tarea.get('colaboradores', []))
    colaboradores = colaboradores_collection.find({'_id': {'$in': list(colaboradores_ids)}})
    emails = [colaborador['email'] for colaborador in colaboradores]
    return jsonify(emails)
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)