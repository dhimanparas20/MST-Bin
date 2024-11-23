from flask import Flask, jsonify, request, render_template, make_response 
from flask_restful import Api, Resource
from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import string
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
api = Api(app)

# MongoDB Configuration
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING')
if not MONGO_CONNECTION_STRING:
    raise ValueError("MONGO_CONNECTION_STRING is not set in the environment variables")

client = MongoClient(MONGO_CONNECTION_STRING)
db = client[os.getenv('MONGO_DB_NAME', 'pastebin')]
pastes_collection = db[os.getenv('MONGO_COLLECTION_NAME', 'pastes')]

# Helper function to generate a random 6-digit key
def generate_key():
    key_length = int(os.getenv('KEY_LENGTH', '6'))
    return ''.join(random.choices(string.ascii_letters + string.digits, k=key_length))

# Resource for saving pastes
class SavePaste(Resource):
    def post(self):
        data = request.json.get('data', '')
        if not data:
            return {'error': 'No data provided'}, 400

        key = generate_key()
        paste = {
            'key': key,
            'data': data,
            'created_at': datetime.now()
        }
        pastes_collection.insert_one(paste)
        return {'url': f'{request.host_url}{key}'}, 201

# Resource for retrieving pastes
class GetPaste(Resource):
    def get(self, key):
        paste = pastes_collection.find_one({'key': key})
        if not paste:
            return {'error': 'Paste not found or Deleted'}, 404

        return make_response(render_template('paste.html', paste=paste['data']))

# Resource for rendering the homepage
class Index(Resource):
    def get(self):
        return make_response(render_template('index.html'))

# Register resources
api.add_resource(SavePaste, '/api/save')
api.add_resource(GetPaste, '/<string:key>')
api.add_resource(Index, '/')

# Background task to delete old pastes
@app.before_request
def delete_expired_pastes():
    expiration_hours = int(os.getenv('EXPIRATION_HOURS', '24'))
    expiration_time = datetime.now() - timedelta(hours=expiration_hours)
    pastes_collection.delete_many({'created_at': {'$lt': expiration_time}})

if __name__ == '__main__':
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        port=int(os.getenv('FLASK_PORT', '5000')),
        threaded=True,
        host=os.getenv('FLASK_HOST', '0.0.0.0')
    )
