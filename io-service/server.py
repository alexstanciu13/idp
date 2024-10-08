import mongoengine
import json
import os


# Responses codes:
#     200 - OK
#     201 - Created
#     400 - Bad Request
#     404 - Not Found
#     409 - Conflict - NonUniqueError


from flask import Flask, request, Response, jsonify
from pymongo import MongoClient
from mongoengine import connect
from db_entities import Houses, Categories

def connect_to_database():
    try:
        client = MongoClient(host=os.getenv('DB_HOSTNAME', 'mongo'),
                             port=int(os.getenv('DB_PORT', 27017)),
                             username=os.getenv('USERNAME_DB', 'admin'),
                             password=os.getenv('PASSWORD_DB', 'admin'),
                             authSource='admin')

        db_name = os.getenv('DB_NAME', 'products_db')
        db = client[db_name]

        connect(
            db=db_name,
            host=os.getenv('DB_HOSTNAME', 'mongo'),
            port=int(os.getenv('DB_PORT', 27017)),
            username=os.getenv('USERNAME_DB', 'admin'),
            password=os.getenv('PASSWORD_DB', 'admin'),
            authentication_source='admin'
        )

        return db

    except:
        print("Error connecting to database!")
        return None

# ------------- Definire aplicatie Flask
app = Flask(__name__)


# ------------ Autentificare la baza de date
db = connect_to_database()
if db is None:
    print("Error connecting to database!")
    exit(1)
else:
    print("Connected to database!")

# ------------- Utility functions
def getRequestBody():
    return request.get_json(silent=True)

def getRequestBodyParam(param):
    return request.args.get(param)

def productSerializer(product):
    return {
        'id': int(product.id),
        'house': str(product.house),
        'price': float(product.price),
        'surface': float(product.surface),
        'description': str(product.description),
        'category': str(product.category.name),
        'username': str(product.username)
    }

def categorySerializer(category):
    return {
        'id': int(category.id),
        'name': str(category.name)
    }


# ------------- Create category endpoint
@app.route('/io/category', methods=['POST'])
def create_category():
    # Extract payload
    payload = getRequestBody()

    if not payload:
        return Response(status=400)
    
    # Extract data from payload
    name = payload.get('name')

    # Check if all required fields are present
    if not name:
        return Response(status=400)
    
    # Create new category
    category = Categories(name=name)
    try:
        category.save()
    except mongoengine.errors.NotUniqueError:
        return Response(status=409)
    except:
        return Response(status=400)
    
    return jsonify({'id': category._id}), 201



# ------------- Get all categories endpoint
@app.route('/io/categories', methods=['GET'])
def get_categories():
    return json.dumps(list(Categories.objects.all()), default=categorySerializer), 200




# ------------- Add new product endpoint
@app.route('/io/houses', methods=['POST'])
def add_product():
    # Extract payload
    payload = getRequestBody()

    if not payload:
        return Response(status=400)
    
    # Extract data from payload
    name = payload.get('house')
    price = payload.get('price')
    surface = payload.get('surface')
    description = payload.get('description')
    category_id = payload.get('category_id')
    username = payload.get('username')

    category = Categories.objects(pk=category_id).get()
    if not category:
        return 'Category not found!', 404
    
    # Check if all required fields are present
    if not name or not price or not surface or not description or not username:
        return Response(status=400)
    else:
        try:
            price = float(price)
            surface = int(surface)
        except:
            return Response(status=400)

    # Create new house
    product = Houses(house=name,
                       price=price,
                       surface=surface,
                       description=description,
                       category=category,
                       username=username)
    try:
        product.save()
    except mongoengine.errors.NotUniqueError:
        return Response(status=409)
    except:
        return Response(status=400)
    
    return jsonify({'id': product.pk}), 201


@app.route('/io/house/<id>', methods=['GET'])
def get_product(id):
    try:
        product = Houses.objects(pk=id).get()
    except:
        return Response(status=404)
    
    return json.dumps(product, default=productSerializer), 200
    

@app.route('/io/house/<id>', methods=['DELETE'])
def delete_product(id):
    try:
        product = Houses.objects(pk=id).get()
    except:
        return Response(status=404)
    
    product.delete()
    return 'Product deleted!', 200


@app.route('/io/house/<id>', methods=['PUT'])
def update_product_quantity(id):
    # Extract payload
    payload = getRequestBody()

    if not payload:
        return Response(status=400)
    
    # Extract data from payload
    surface = payload.get('surface')
    price = payload.get('price')
    description = payload.get('description')
    category_id = payload.get('category_id')
    house = payload.get('house')

    try:
        product = Houses.objects(pk=id).get()
    except:
        return 'Product not found!', 404
    
    if surface:
        try:
            surface = float(surface)
            product.surface = surface
        except:
            return Response(status=400)
        
    if price:
        try:
            price = float(price)
            product.price = price
        except:
            return Response(status=400)
    
    if description:
        product.description = description
    
    if category_id:
        try:
            category = Categories.objects(pk=category_id).get()
            product.category = category
        except:
            return Response(status=400)
        
    if house:
        product.product = house

    product.save()
    return json.dumps(product, default=productSerializer), 200



# ------------- Get all products endpoint
@app.route('/io/houses', methods=['GET'])
def get_products():
    return json.dumps(list(Houses.objects.all()), default=productSerializer), 200

# ------------- Definire rute
@app.route('/')
def hello_world(): 
    return "Hello World from IO/SERVICE!"


# ------------- Pornire server Flask
if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)