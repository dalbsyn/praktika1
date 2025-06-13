import json
import random
import uuid

from marshmallow import ValidationError
from app.schemas import CryptopayRequestSchema, CryptogramSchema

from flask import Blueprint, jsonify, request, current_app

# Инициализация Blueprint
main_bp = Blueprint('main', __name__)
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

# Инициализация схем валидации
cryptopay_request_schema = CryptopayRequestSchema()
cryptogram_schema = CryptogramSchema()


def init_app(app):
    # Инициализация приложения
    app.register_blueprint(main_bp)
    app.register_blueprint(payment_bp)


@main_bp.route('/', methods=['GET'])
def home():
    """
    Проверка работоспособности вообще
    """
    return jsonify(message="Эмулятор работает"), 200


@payment_bp.route('/cryptopay/', methods=['POST'])
def cryptopay():
    """
    Эндпоинт для эмуляции платежей с использованием криптограммы.
    На текущий момент обрабатывает платежи без 3DS.
    """

    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                "code": 400, "message": "Bad Request: Empty or invalid JSON body.",
                "id": "", "reference": "", "accountId": ""
            }), 400

        # Валидация входных данных
        try:
            validated_data = cryptopay_request_schema.load(request_data)
        except ValidationError as err:
            return jsonify({
                "code": 400,
                "message": "Bad Request: Validation error.",
                "errors": err.messages,
                "invoiceId": request_data.get('invoiceId', ''),
                "id": "",
                "reference": "",
                "accountId": request_data.get('accountId', '')
            }), 400

        # Получение данных из словаря уже валидированных значений
        amount = validated_data['amount']
        currency = validated_data['currency']
        name = validated_data['name']
        cryptogram_str = validated_data['cryptogram']
        invoice_id = validated_data['invoiceId']
        description = validated_data['description']
        post_link = validated_data['postLink']
        card_save = validated_data['cardSave']
        invoice_id_alt = validated_data.get('invoiceIdAlt')
        account_id = validated_data.get('accountId')
        email = validated_data.get('email')
        phone = validated_data.get('phone')
        failure_post_link = validated_data.get('failurePostLink')
        data_str = validated_data.get('data')

        # Считывание и валидация содержимого криптограммы
        try:
            cryptogram_raw_data = json.loads(cryptogram_str)
            cryptogram_data = cryptogram_schema.load(cryptogram_raw_data)
        except json.JSONDecodeError:
            return jsonify({
                "code": 400,
                "message": "Bad Request: Invalid cryptogram format (not a valid JSON string).",
                "invoiceId": invoice_id, "id": "", "reference": "", "accountId": account_id
            }), 400
        except ValidationError as err:
            return jsonify({
                "code": 400,
                "message": "Bad Request: Cryptogram validation error.",
                "errors": err.messages,
                "invoiceId": invoice_id, "id": "", "reference": "", "accountId": account_id
            }), 400

        card_number = cryptogram_data['hpan']
        exp_date = cryptogram_data['expDate']
        cvc = cryptogram_data['cvc']
        terminal_id = cryptogram_data.get('terminalId')

        # Считывание data, если оно есть
        data_parsed = None
        if data_str:
            try:
                data_parsed = json.loads(data_str)
            except json.JSONDecodeError:
                return jsonify({
                    "code": 400,
                    "message": "Bad Request: Invalid 'data' format (must be a JSON string).",
                    "invoiceId": invoice_id, "id": "", "reference": "", "accountId": account_id
                }), 400

        # Проверка номера карты на его наличие в списке таковых с ошибками
        error_code_for_card = current_app.config['ERROR_CARD_NUMBERS'].get(card_number)

        if error_code_for_card is not None:
            error_message = current_app.config['EPAY_ERROR_CODES'].get(
                error_code_for_card,
                "Неизвестная ошибка: Код ошибки не найден в EPAY_ERROR_CODES."
            )
            return jsonify({
                "code": error_code_for_card,
                "message": error_message,
                "invoiceId": invoice_id,
                "id": str(uuid.uuid4()),
                "reference": "",
                "accountId": account_id
            }), 400

        # Генерация других численных значений для ответа
        transaction_id = str(uuid.uuid4())
        reference = ''.join(random.choices('0123456789', k=12))
        int_reference = uuid.uuid4().hex.upper()[:16]
        approval_code = ''.join(random.choices('0123456789', k=6))
        card_id = str(uuid.uuid4())

        # Успешный ответ
        response_data = {
            "id": transaction_id,
            "accountId": account_id if account_id else "",
            "amount": amount,
            "amountBonus": 0,
            "currency": currency,
            "description": description,
            "email": email if email else "",
            "invoiceID": invoice_id,
            "language": "rus",
            "phone": phone if phone else "",
            "reference": reference,
            "intReference": int_reference,
            "secure3D": None,
            "cardID": card_id,
            "fee": 0,
            "approvalCode": approval_code,
            "code": 0,
            "status": "AUTH",
            "secureDetails": "",
            "qrReference": "",
            "ip": request.remote_addr or "127.0.0.1",
            "ipCity": "", "ipCountry": "", "ipDistrict": "",
            "ipLatitude": 0, "ipLongitude": 0, "ipRegion": "",
            "issuerBankCountry": "KAZ",
            "isCredit": False
        }
        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Internal Server Error: {str(e)}",
            "id": "",
            "reference": "",
            "accountId": ""
        }), 500
