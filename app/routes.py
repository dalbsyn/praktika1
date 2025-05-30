from flask import Blueprint, jsonify, request
from app.services import get_welcome_message, get_example_data

bp = Blueprint('main', __name__)

# bank_emulator/app/routes.py
from flask import Blueprint, jsonify, request
from app.services import get_welcome_message, get_example_data, process_hold_funds # Добавляем импорт process_hold_funds

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    message = get_welcome_message()
    return jsonify({'message': message})

@bp.route('/example', methods=['GET'])
def example_endpoint():
    data = get_example_data()
    return jsonify({'data': data})

@bp.route('/api/operation/<string:operation_id>/hold', methods=['POST'])
def hold_funds_endpoint(operation_id: str):
    '''
    Эндпоинт для удержания средств на счету.

    Входные аргументы:
    - operation_id - UUID.

    Выходные данные:
    - JSON-ответ (см. services.py - process_hold_funds());
    - Код ответа:
        - 200 - операция существует;
        - 201 - запрос выполнен;
        - 400 - ошибка в запросе;
        - 500 - другая ошибка.
    
    Сперва ведется проверка входных данных. После успешной проверки выполняется удержание требуемого значения на счету.
    '''

    data = request.get_json()

    if not data:
        return jsonify({'message': 'Требуется JSON-тело запроса.'}), 400
    if 'account_identifier' not in data or not data['account_identifier']:
        return jsonify({'message': 'Поле "account_identifier" обязательно.'}), 400
    if 'amount' not in data or not isinstance(data['amount'], (int, float)):
        return jsonify({'message': 'Поле "amount" обязательно и должно быть числом.'}), 400
    if 'description' not in data or not data['description']:
        return jsonify({'message': 'Поле "description" обязательно.'}), 400

    account_identifier = data['account_identifier']
    amount = float(data['amount'])
    description = data['description']

    try:
        result = process_hold_funds(operation_id, account_identifier, amount, description)
        if "Операция удержания с данным ID уже существует" in result.get("message", ""):
            return jsonify(result), 200
        else:
            return jsonify(result), 201

    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': 'Произошла внутренняя ошибка сервера.', 'error': str(e)}), 500
