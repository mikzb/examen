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
db = client.parcial2
peliculas_collection = db.peliculas # titulo (titulo), URI de su imagen de cartel (imagen)
salas_collection = db.salas #nombre (nombre), email del propietario(email), coordenadas gps (coordenadas)
# Colección para proyecciones
proyecciones_collection = db.proyecciones  # pelicula_id, sala_id, timestamp


# CRUD para películas

@app.route('/peliculas', methods=['POST'])
def create_pelicula():
    data = request.json
    result = peliculas_collection.insert_one(data)
    return jsonify({'_id': str(result.inserted_id)}), 201

@app.route('/peliculas', methods=['GET'])
def get_peliculas():
    peliculas = list(peliculas_collection.find())
    for pelicula in peliculas:
        pelicula['_id'] = str(pelicula['_id'])
    return jsonify(peliculas), 200

@app.route('/peliculas/<id>', methods=['GET'])
def get_pelicula(id):
    pelicula = peliculas_collection.find_one({'_id': ObjectId(id)})
    if pelicula:
        pelicula['_id'] = str(pelicula['_id'])
        return jsonify(pelicula), 200
    return jsonify({'error': 'Pelicula no encontrada'}), 404

@app.route('/peliculas/<id>', methods=['PUT'])
def update_pelicula(id):
    data = request.json
    result = peliculas_collection.update_one({'_id': ObjectId(id)}, {'$set': data})
    if result.matched_count:
        return jsonify({'message': 'Pelicula actualizada'}), 200
    return jsonify({'error': 'Pelicula no encontrada'}), 404

@app.route('/peliculas/<id>', methods=['DELETE'])
def delete_pelicula(id):
    result = peliculas_collection.delete_one({'_id': ObjectId(id)})
    if result.deleted_count:
        return jsonify({'message': 'Pelicula eliminada'}), 200
    return jsonify({'error': 'Pelicula no encontrada'}), 404

# CRUD para salas de cine

@app.route('/salas', methods=['POST'])
def create_sala():
    data = request.json
    result = salas_collection.insert_one(data)
    return jsonify({'_id': str(result.inserted_id)}), 201

@app.route('/salas', methods=['GET'])
def get_salas():
    salas = list(salas_collection.find())
    for sala in salas:
        sala['_id'] = str(sala['_id'])
    return jsonify(salas), 200

@app.route('/salas/<id>', methods=['GET'])
def get_sala(id):
    sala = salas_collection.find_one({'_id': ObjectId(id)})
    if sala:
        sala['_id'] = str(sala['_id'])
        return jsonify(sala), 200
    return jsonify({'error': 'Sala no encontrada'}), 404

@app.route('/salas/<id>', methods=['PUT'])
def update_sala(id):
    data = request.json
    result = salas_collection.update_one({'_id': ObjectId(id)}, {'$set': data})
    if result.matched_count:
        return jsonify({'message': 'Sala actualizada'}), 200
    return jsonify({'error': 'Sala no encontrada'}), 404

@app.route('/salas/<id>', methods=['DELETE'])
def delete_sala(id):
    result = salas_collection.delete_one({'_id': ObjectId(id)})
    if result.deleted_count:
        return jsonify({'message': 'Sala eliminada'}), 200
    return jsonify({'error': 'Sala no encontrada'}), 404

# Asignar proyección
@app.route('/proyecciones', methods=['POST'])
def create_proyeccion():
    data = request.json
    result = proyecciones_collection.insert_one(data)
    return jsonify({'_id': str(result.inserted_id)}), 201

# Buscar proyección por título de película
@app.route('/proyecciones/<titulo>', methods=['GET'])
def get_proyecciones_by_titulo(titulo):
    pelicula = peliculas_collection.find_one({'titulo': titulo})
    if not pelicula:
        return jsonify({'error': 'Pelicula no encontrada'}), 404

    proyecciones = list(proyecciones_collection.find({'pelicula_id': pelicula['_id']}))
    for proyeccion in proyecciones:
        proyeccion['_id'] = str(proyeccion['_id'])
        proyeccion['pelicula_id'] = str(proyeccion['pelicula_id'])
        proyeccion['sala_id'] = str(proyeccion['sala_id'])
        
        sala = salas_collection.find_one({'_id': ObjectId(proyeccion['sala_id'])})
        if sala:
            proyeccion['sala'] = sala

    return jsonify(proyecciones), 200

# Cartelera
@app.route('/cartelera/<nombre_sala>', methods=['GET'])
def get_cartelera(nombre_sala):
    sala = salas_collection.find_one({'nombre': nombre_sala})
    if not sala:
        return jsonify({'error': 'Sala no encontrada'}), 404

    proyecciones = list(proyecciones_collection.find({'sala_id': sala['_id']}).sort('timestamp', 1))
    for proyeccion in proyecciones:
        proyeccion['_id'] = str(proyeccion['_id'])
        proyeccion['pelicula_id'] = str(proyeccion['pelicula_id'])
        proyeccion['sala_id'] = str(proyeccion['sala_id'])
        
        pelicula = peliculas_collection.find_one({'_id': ObjectId(proyeccion['pelicula_id'])})
        if pelicula:
            proyeccion['pelicula'] = pelicula

    return jsonify(proyecciones), 200

# Recomendar por fecha
@app.route('/recomendar/fecha', methods=['GET'])
def recomendar_por_fecha():
    fecha_str = request.args.get('fecha')
    fecha = datetime.fromisoformat(fecha_str)
    
    proyeccion = proyecciones_collection.find_one({'timestamp': {'$gte': fecha}}, sort=[('timestamp', 1)])
    if not proyeccion:
        return jsonify({'error': 'No hay proyecciones a partir de la fecha indicada'}), 404

    proyeccion['_id'] = str(proyeccion['_id'])
    proyeccion['pelicula_id'] = str(proyeccion['pelicula_id'])
    proyeccion['sala_id'] = str(proyeccion['sala_id'])
    
    pelicula = peliculas_collection.find_one({'_id': ObjectId(proyeccion['pelicula_id'])})
    sala = salas_collection.find_one({'_id': ObjectId(proyeccion['sala_id'])})
    
    if pelicula:
        proyeccion['pelicula'] = pelicula
    if sala:
        proyeccion['sala'] = sala

    return jsonify(proyeccion), 200

# Recomendar por cercanía
@app.route('/recomendar/cercania', methods=['GET'])
def recomendar_por_cercania():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    user_location = (lat, lon)
    
    salas = list(salas_collection.find())
    if not salas:
        return jsonify({'error': 'No hay salas disponibles'}), 404

    closest_sala = min(salas, key=lambda sala: geodesic(user_location, (sala['coordenadas']['lat'], sala['coordenadas']['lon'])).miles)
    
    proyeccion = proyecciones_collection.find_one({'sala_id': closest_sala['_id']}, sort=[('timestamp', 1)])
    if not proyeccion:
        return jsonify({'error': 'No hay proyecciones en la sala más cercana'}), 404

    proyeccion['_id'] = str(proyeccion['_id'])
    proyeccion['pelicula_id'] = str(proyeccion['pelicula_id'])
    proyeccion['sala_id'] = str(proyeccion['sala_id'])
    
    pelicula = peliculas_collection.find_one({'_id': ObjectId(proyeccion['pelicula_id'])})
    
    if pelicula:
        proyeccion['pelicula'] = pelicula
    proyeccion['sala'] = closest_sala

    return jsonify(proyeccion), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)