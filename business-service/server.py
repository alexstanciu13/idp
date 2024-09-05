from flask import Flask, Response, jsonify
import requests
from utils import partial_match, getRequestBody, createProductRequest, token_required
from influxdb import InfluxDBClient

def database_exists(name):
        existing_databases = db_client.get_list_database()
        for database in existing_databases:
            if database["name"] == name:
                return True
        return False

# ------------- Define Flask application
app = Flask(__name__)

# InfluxDB client
db_client = InfluxDBClient(host='influxdb', port=8086)

# connect to InfluxDB
if not database_exists("idp"):
    db_client.create_database("idp")
db_client.switch_database("idp")

category_counter = 0
product_counter = 0

# ------------- Utility functions
def getOrCreateCategory(category):
    # Call io-service endpoint to create or assign category
    response = requests.get('http://io-service:5001/io/categories')
    categories = response.json()
    category_exists = False
    category_id = None
    for c in categories:
        if c['name'].lower() == category.lower():
            category_exists = True
            category_id = c['id']
            break
    if not category_exists:
        response = requests.post('http://io-service:5001/io/category', json={'name': category})
        category_id = response.json()['id']

        # Update metrics
        global category_counter 
        category_counter += 1
        json_body = [
            {
                "measurement": "categories",
                "fields": {
                    "value": category_counter
                }
            }
        ]
        db_client.write_points(json_body)
    
    return category_id

@app.route('/business/houses', methods=['POST'])
@token_required
def add_product(token_payload):
    # Only allow owners to add products
    if token_payload.get('type') != 'owner':
        return Response(status=403)
    
    # Extract payload
    payload = getRequestBody()

    if not payload:
        return Response(status=400)
    
    # Extract data from payload
    name = payload.get('house')
    price = payload.get('price')
    surface = payload.get('surface')
    description = payload.get('description')
    category = payload.get('category')

    # Check if all required fields are present
    if not name or not price or not surface or not description:
        return Response(status=400)
    else:
        # Convert to correct data types
        try:
            price = float(price)
            surface = int(surface)
        except:
            return 'Price and surface must be numbers', 400
        
        # Check if fields are valid
        if price < 0 or surface < 0:
            return 'Price and surface must be positive', 400
        if len(name) == 0 or len(description) == 0:
            return 'Name and description must not be empty', 400
        
        # Check if category is present or assign default
        if not category:
            category = 'Others'
    
    category_id = getOrCreateCategory(category)

    # Call io-service endpoint to create product
    username = token_payload.get('username')
    payload = createProductRequest(name, price, surface, description, category_id, username)
    
    response = requests.post('http://io-service:5001/io/houses', json=payload)

    # Update metrics
    if response.status_code == 201:
        global product_counter
        product_counter += 1
        json_body = [
            {
                "measurement": "products",
                "fields": {
                    "value": product_counter
                }
            }
        ]
        db_client.write_points(json_body)
    
    return Response(status=response.status_code)

# ------------- Get all products
@app.route('/business/houses', methods=['GET'])
@token_required
def get_products(token_payload):
    # Call io-service endpoint to get all products
    response = requests.get('http://io-service:5001/io/houses')
    
    return jsonify(response.json())

# ------------- Get all products posted by current owner
@app.route('/business/houses/personal', methods=['GET'])
@token_required
def get_personal_products(token_payload):
    # Only allow owners to view their own products
    if token_payload.get('type') != 'owner':
        return Response(status=403)
    
    # Call io-service endpoint to get all products
    response = requests.get('http://io-service:5001/io/houses')
    products = response.json()

    # Filter products by owner
    username = token_payload.get('username')
    products = [p for p in products if p['username'] == username]
    
    return jsonify(products)

# ------------- Get all products by category
@app.route('/business/houses/category/<category>', methods=['GET'])
@token_required
def get_products_by_category(token_payload, category):
    # Get all products
    response = requests.get('http://io-service:5001/io/houses')
    products = response.json()

    # Filter products by category
    products = [p for p in products if p['category'].lower() == category.lower()]
    
    return jsonify(products)

# ------------- Get all products by owner
@app.route('/business/houses/owner/<owner>', methods=['GET'])
@token_required
def get_products_by_owner(token_payload, owner):
    # Get all products
    response = requests.get('http://io-service:5001/io/houses')
    products = response.json()

    # Filter products by owner
    products = [p for p in products if p['username'] == owner]
    
    return jsonify(products)

# ------------- Search products by name
@app.route('/business/houses/search/<keyname>', methods=['GET'])
@token_required
def search_products(token_payload, keyname):
    # Get all houses
    response = requests.get('http://io-service:5001/io/houses')
    products = response.json()

    # Filter houses by name (allow partial match)
    products = [p for p in products if keyname.lower() in p['house'].lower() or partial_match(keyname, p['house'])]
    
    return jsonify(products)

# ------------- Delete a product
@app.route('/business/houses/<id>', methods=['DELETE'])
@token_required
def delete_product(token_payload, id):
    # Only allow owners to delete products
    if token_payload.get('type') != 'owner':
        return Response(status=403)
    
    # Check if product exists and belongs to owner
    response = requests.get(f'http://io-service:5001/io/house/{id}')
    if response.status_code == 404:
        return Response(status=404)
    
    product = response.json()
    if product['username'] != token_payload.get('username'):
        return Response(status=403)
    
    # Call io-service endpoint to delete product
    response = requests.delete(f'http://io-service:5001/io/house/{id}')

    # Update metrics
    if response.status_code == 200:
        global product_counter
        product_counter -= 1
        json_body = [
            {
                "measurement": "products",
                "fields": {
                    "value": product_counter
                }
            }
        ]
        db_client.write_points(json_body)

    return Response(status=response.status_code)

# ------------- Update a product
@app.route('/business/house/<id>', methods=['PUT'])
@token_required
def update_product(token_payload, id):
    # Only allow owners to update products
    if token_payload.get('type') != 'owner':
        return Response(status=403)
    
    # Check if product exists and belongs to owner
    response = requests.get(f'http://io-service:5001/io/house/{id}')
    if response.status_code == 404:
        return Response(status=404)
    
    product = response.json()
    if product['username'] != token_payload.get('username'):
        return Response(status=403)
    
    # Extract payload
    payload = getRequestBody()

    if not payload:
        return Response(status=400)
    
    # Extract data from payload
    name = payload.get('house')
    price = payload.get('price')
    surface = payload.get('surface')
    description = payload.get('description')
    category = payload.get('category')

    # Compose new payload
    new_payload = {}
    if name:
        if len(name) == 0:
            return 'Name must not be empty', 400
        new_payload['house'] = name
    
    if price:
        try:
            price = float(price)
            if price < 0:
                return 'Price must be positive', 400
        except:
            return 'Price must be a number', 400
        new_payload['price'] = price
        
    if surface:
        try:
            surface = int(surface)
            if surface < 0:
                return 'surface must be positive', 400
        except:
            return 'surface must be an integer', 400
        new_payload['surface'] = surface
        
    if description:
        if len(description) == 0:
            return 'Description must not be empty', 400
        new_payload['description'] = description
        
    if category:
        category_id = getOrCreateCategory(category)
        new_payload['category_id'] = category_id
    
    # Call io-service endpoint to update product
    response = requests.put(f'http://io-service:5001/io/house/{id}', json=new_payload)
    
    return Response(status=response.status_code)
# ------------- Start Flask server
if __name__ == '__main__':
    app.run('0.0.0.0', port=4107, debug=True)