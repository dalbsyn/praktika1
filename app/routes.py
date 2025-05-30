from flask import Blueprint, jsonify, request
from app.services import get_welcome_message, get_example_data

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    message = get_welcome_message()
    return jsonify({'message': message})

@bp.route('/example', methods=['GET'])
def example_endpoint():
    data = get_example_data()
    return jsonify({'data': data})

