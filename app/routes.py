from flask import Blueprint, jsonify, current_app

# Инициализация Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET'])
def home():
    """
    Проверка работоспособности вообще
    """
    return jsonify(message="Эмулятор работает"), 200

def init_app(app):
    app.register_blueprint(main_bp)