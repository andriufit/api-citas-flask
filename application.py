from flask import Flask
from flask import jsonify
from flask import request

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

from datetime import datetime

from flasgger import Swagger

import pymongo
import bcrypt

from flask_cors import CORS


app = Flask(__name__)

CORS(app)

app.config["JWT_SECRET_KEY"] = "misuperclavedeldestinofinal"

jwt = JWTManager(app)
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "API de Clínica",
        "description": "Documentación de la API para agendar citas",
        "version": "0.0.1",
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Añade 'Bearer <tu_token>' para autenticación"
        }
    },
    "security": [{"Bearer": []}]
})

myclient = pymongo.MongoClient("mongodb://localhost:27017/")


@app.route('/', methods=['GET'])
def hello():
    return 'Hello, World!'


@app.route('/login', methods=['POST'])
def login():
    """
    Iniciar sesión en la aplicación
    ---
    tags:
      - Autenticación
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Token de acceso generado correctamente
      401:
        description: Credenciales incorrectas
    """
    mydb = myclient["Clinica"]
    mycol = mydb["usuarios"]

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    print(username)
    print(password)

    if not username or not password:
        return jsonify({"msg": "Bad username or password"}), 401

    user = mycol.find_one({"username": username})

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    else:
        return jsonify({"msg": "Bad username or password"}), 401


@app.route("/register", methods=['POST'])
def register():
    """
    Registrar un nuevo usuario
    ---
    tags:
        - Autenticación
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                username:
                    type: string
                password:
                    type: string
                name:
                    type: string
                lastname:
                    type: string
                email:
                    type: string
                phone:
                    type: string
                date:
                    type: string
                    format: date
                    example: "25/12/2025"
                    description: Fecha de nacimiento en formato DD/MM/YYYY
    responses:
        200:
            description: Usuario creado correctamente
        400:
            description: Solicitud incorrecta
    """
    mydb = myclient["Clinica"]
    mycol = mydb["usuarios"]

    username = request.json.get('username', None)
    password = request.json.get('password', None)
    name = request.json.get('name', None)
    lastname = request.json.get('lastname', None)
    email = request.json.get('email', None)
    phone = request.json.get('phone', None)
    date = request.json.get('date', None)

    try:
        date = datetime.strptime(date, '%d/%m/%Y').strftime('%d/%m/%Y')
    except ValueError:
        return jsonify({"msg": "Invalid date format"}), 400

    if username is None or password is None:
        return jsonify({"msg": "Bad request"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    password = hashed_password.decode('utf-8')

    user = {
        "username": username,
        "password": password,
        "name": name,
        "lastname": lastname,
        "email": email,
        "phone": phone,
        "date": date
    }
    x = mycol.insert_one(user)

    return jsonify({"msg": "user created"}), 200


@app.route("/centers", methods=['GET'])
@jwt_required()
def center():
    """
    Obtiene una lista de todos los centros
    ---
    tags:
      - Centros
    security:
      - Bearer: []
    summary: Obtiene una lista de todos los centros
    description: Devuelve una lista en formato JSON de todos los centros disponibles en la base de datos "Clinica".
    responses:
      200:
        description: Lista de centros
        schema:
          type: array
          items:
            type: object
            properties:
              nombre:
                type: string
                description: Nombre del centro
              direccion:
                type: string
                description: Dirección del centro
              telefono:
                type: string
                description: Teléfono del centro
    """

    mydb = myclient["Clinica"]
    mycol = mydb["centros"]
    centers = mycol.find({}, {"_id": 0})
    return jsonify(list(centers))


@app.route("/profile", methods=['GET'])
@jwt_required()
def profile():
    """
    Obtiene el perfil del usuario actual
    ---
    tags:
        - Perfil
    security:
        - Bearer: []
    summary: Obtiene el perfil del usuario actual
    description: Devuelve la información del perfil del usuario autenticado en formato JSON.
    responses:
        200:
            description: Perfil del usuario
            schema:
                type: object
                properties:
                    username:
                        type: string
                        description: Nombre de usuario
                    name:
                        type: string
                        description: Nombre del usuario
                    lastname:
                        type: string
                        description: Apellido del usuario
                    email:
                        type: string
                        description: Correo electrónico del usuario
                    phone:
                        type: string
                        description: Teléfono del usuario
                    date:
                        type: string
                        description: Fecha de nacimiento del usuario
                        example: "25/12/2025"
    """
    current_user = get_jwt_identity()
    mydb = myclient["Clinica"]
    mycol = mydb["usuarios"]
    user = mycol.find_one({"username": current_user}, {"_id": 0, "password": 0})
    return jsonify(user)


@app.route("/date/create", methods=['POST'])
@jwt_required()
def createDate():
    
    """
    Crea una nueva cita en la base de datos.
    ---
    tags:
        - Citas
    security:
        - Bearer: []
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                center:
                    type: string
                    description: Nombre del centro, tiene que ser un nombre devuelto por la llamada /centers
                    example: "Centro de Salud"
                date:
                    type: string
                    description: Fecha de nacimiento en formato DD/MM/YYYY HH:00:00
                    example: "25/12/2025 14:00:00"
    responses:
        200:
            description: Usuario creado correctamente
        400:
            description: Solicitud incorrecta o fecha ya reservada
    """

    current_user = get_jwt_identity()
    mydb = myclient["Clinica"]
    mycol = mydb["citas"]
    myCenters = mydb["centros"]

    date = request.json.get('date', None)
    center = request.json.get('center', None)

    existing_center = myCenters.find_one({"name": center})
    if not existing_center:
        return jsonify({"msg": "Center not found"}), 400

    try:
        date = datetime.strptime(date, '%d/%m/%Y %H:00:00')
        day = date.strftime('%d/%m/%Y')
        hour = date.strftime('%H')
    except ValueError:
        return jsonify({"msg": "Invalid date format"}), 400
    

    existing_date = mycol.find_one({"day": day, "hour": hour})
    if existing_date:
        return jsonify({"msg": "Date and hour already taken"}), 400

    new_date = {
        "username": current_user,
        "day": day,
        "hour": hour,
        "created_at": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        "center": request.json.get('center', None)
    }
    mycol.insert_one(new_date)

    return jsonify({"msg": "Date created successfully"}), 200


@app.route("/date/getByDay", methods=['POST'])
@jwt_required()
def getDatesByDay():
    """
    Obtiene las citas por día.
    ---
    tags:
        - Citas
    security:
        - Bearer: []
    parameters:
        - name: day
          in: body
          type: string
          required: true
          description: El día para el cual se desean obtener las citas, entre 1 y 31.
    responses:
        200:
            description: Una lista de citas para el día especificado.
            schema:
                type: array
                items:
                    type: object
                    properties:
                        day:
                            type: string
                            description: El día de la cita.
                        cancel:
                            type: integer
                            description: Estado de cancelación de la cita.
        400:
            description: Solicitud incorrecta, el parámetro 'day' es requerido.
    """

    mydb = myclient["Clinica"]
    mycol = mydb["citas"]
    date = request.json.get('day', None)
    

    try:
        date_validation = datetime.strptime(date, "%d/%m/%Y")  
        day = date_validation.day
        if not day or (day > 31 or day < 1):
            return jsonify({"msg": "Bad request"}), 400
        dates = mycol.find({"day": date, "cancel": {"$ne": 1}}, {"_id": 0})
        return jsonify(format_dates(list(dates)))
    except ValueError:
        return jsonify({"msg": "Invalid date format, use DD/MM/YYYY"}), 400



@app.route("/date/getByUser", methods=['GET'])
@jwt_required()
def getDateByUser():
    """
    Obtiene las citas del usuario logeado
    ---
    tags:
        - Citas
    summary: Obtiene las citas del usuario logeado.
    description: Esta función recupera todas las citas de un usuario autenticado que no han sido canceladas.
    responses:
        200:
            description: Una lista de citas del usuario.
            content:
                application/json:
                    schema:
                        type: array
                        items:
                            type: object
                            properties:
                                username:
                                    type: string
                                    description: Nombre de usuario.
                                date:
                                    type: string
                                    example: "25/12/2025 14:00:00"
                                    description: Fecha y hora de la cita.
                                other_fields:
                                    type: string
                                    description: Otros campos relevantes de la cita.
    """

    current_user = get_jwt_identity()
    mydb = myclient["Clinica"]
    mycol = mydb["citas"]

    dates = mycol.find({"username": current_user, "cancel": {"$ne": 1}}, {"_id": 0})
    return jsonify(format_dates(list(dates)))


@app.route("/date/delete", methods=['POST'])
@jwt_required()
def deleteDate():
    """
    Cancela una cita existente
    ---
    tags:
        - Citas
    summary: Cancela una cita existente
    description: Permite a un usuario autenticado cancelar una cita existente en la base de datos.
    parameters:
        - in: body
          name: body
          schema:
            type: object
            required:
                - date
                - center
            properties:
                date:
                    type: string
                    description: Fecha y hora de la cita en formato 'dd/mm/yyyy HH:00:00'
                    example: "25/12/2025 14:00:00"
                center:
                    type: string
                    description: Centro donde se realizará la cita
    responses:
        200:
            description: Cita eliminada exitosamente
            schema:
                type: object
                properties:
                    msg:
                        type: string
                        example: Date deleted successfully
        400:
            description: Formato de fecha inválido o cita no encontrada
            schema:
                type: object
                properties:
                    msg:
                        type: string
                        example: Invalid date format
        401:
            description: Usuario no autorizado para eliminar la cita
            schema:
                type: object
                properties:
                    msg:
                        type: string
                        example: Unauthorized
    """


    current_user = get_jwt_identity()
    mydb = myclient["Clinica"]
    mycol = mydb["citas"]

    date = request.json.get('date', None)
    center = request.json.get('center', None)

    try:
        date = datetime.strptime(date, '%d/%m/%Y %H:00:00')
        day = date.strftime('%d/%m/%Y')
        hour = date.strftime('%H')
    except ValueError:
        return jsonify({"msg": "Invalid date format"}), 400

    date = mycol.find_one({"day": day, "hour": hour, "center": center})
    if not date:
        return jsonify({"msg": "Date not found"}), 400

    if date["username"] != current_user:
        return jsonify({"msg": "Unauthorized"}), 401

    mycol.update_one(
        {"day": day, "hour": hour, "center": center},
        {"$set": {"cancel": 1}}
    )

    return jsonify({"msg": "Date deleted successfully"}), 200


@app.route("/dates", methods=['GET'])
@jwt_required()
def getDates():
    """
    Obtiene las citas no canceladas del usuario actual.
    ---
    tags:
        - Citas
    responses:
        200:
            description: Una lista de citas no canceladas.
            schema:
                type: array
                items:
                    type: object
                    properties:
                        fecha:
                            type: string
                            description: La fecha de la cita.
                        hora:
                            type: string
                            description: La hora de la cita.
                        paciente:
                            type: string
                            description: El nombre del paciente.
                        doctor:
                            type: string
                            description: El nombre del doctor.
    """

    current_user = get_jwt_identity()
    mydb = myclient["Clinica"]
    mycol = mydb["citas"]

    dates = mycol.find({"cancel": {"$ne": 1}}, {"_id": 0})
   
    return jsonify(format_dates(list(dates)))

@app.route("/migracion", methods=['GET'])
def migracion():

    dblist = myclient.list_database_names()
    if "Clinica" not in dblist:
        mydb = myclient["Clinica"]
        collections = ["usuarios", "centros", "citas"]

        for collection in collections:
            mydb.create_collection(collection)

        # Insert two centers related to Madrid
        mydb["centros"].insert_many([
            {"name": "Centro de Salud Madrid Norte", "address": "Calle de la Salud, 123, Madrid"},
            {"name": "Centro Médico Madrid Sur", "address": "Avenida de la Medicina, 456, Madrid"}
        ])

        return jsonify({"msg": "Database and collections created"}), 200
    else:
        return jsonify({"msg": "Database already exists"}), 200


@app.route("/currentUser", methods=["PATCH"])
@jwt_required()
def patchCurrentuser():
    """
    Actualizar datos del usuario logeado
    ---
    tags:
        - Perfil
    parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
                name:
                    type: string
                lastname:
                    type: string
                email:
                    type: string
                phone:
                    type: string
                date:
                    type: string
                    format: date
                    example: "25/12/2025"
                    description: Fecha de nacimiento en formato DD/MM/YYYY
    responses:
        200:
            description: Usuario creado correctamente
        400:
            description: Usuario no existe
    """
    current_user = get_jwt_identity()
    mydb = myclient["Clinica"]
    mycol = mydb["usuarios"]

    name = request.json.get('name', None)
    lastname = request.json.get('lastname', None)
    email = request.json.get('email', None)
    phone = request.json.get('phone', None)
    date = request.json.get('date', None)

    newData = {}

    if name:
        newData["name"] = name

    if lastname:
        newData["lastname"] = lastname

    if email:
        newData["email"] = email

    if phone:
        newData["phone"] = phone

    if date:
        try:
            date = datetime.strptime(date, '%d/%m/%Y').strftime('%d/%m/%Y')
        except ValueError:
            return jsonify({"msg": "Invalid date format"}), 400

        newData["date"] = date

    print(current_user)

    update_result = mycol.update_one(
        {"username": current_user},
        {"$set": newData}  
    )

    if update_result.matched_count == 0:
        return jsonify({"msg": "User not found"}), 404

    return jsonify({"msg": "User updated"}), 201


def format_dates(dates):
    result = []
    for date in dates:
        date['date'] = f"{date['day']} {date['hour']}:00:00"
        del date['day']
        del date['hour']
        result.append(date)

    result.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y %H:00:00'))
    return result