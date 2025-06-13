import json
import random
import uuid

from flask import Blueprint, jsonify, request, current_app

# Инициализация Blueprint
main_bp = Blueprint('main', __name__)
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

@main_bp.route('/', methods=['GET'])
def home():
    """
    Проверка работоспособности вообще
    """
    return jsonify(message="Эмулятор работает"), 200


@payment_bp.route('/cryptopay/', methods=['POST'])
def cryptopay():
    """
    Эндпоинт для эмуляции платежей с использованием криптограммы
    """
    current_app.logger.info("Получен запрос к /api/payment/cryptopay/")

    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                "code": 400,
                "message": "Bad Request: Empty or invalid JSON body.",
                "id": "",
                "reference": "",
                "accountId": ""
            }), 400

        # Считывание и валидация некоторых значений
        amount = request_data.get('amount')
        currency = request_data.get('currency')
        invoice_id = request_data.get('invoiceId')
        account_id = request_data.get('accountId')
        cryptogram_str = request_data.get('cryptogram')

        if not all([amount, currency, invoice_id, cryptogram_str]):
            return jsonify({
                "code": 400,
                "message": "Bad Request: Missing required fields (amount, currency, invoiceId, cryptogram).",
                "invoiceId": invoice_id,
                "id": "",
                "reference": "",
                "accountId": account_id
            }), 400

        # Считывание и валидация криптограммы
        try:
            cryptogram_data = json.loads(cryptogram_str)
        except json.JSONDecodeError:
            return jsonify({
                "code": 400,
                "message": "Bad Request: Invalid cryptogram format.",
                "invoiceId": invoice_id,
                "id": "",
                "reference": "",
                "accountId": account_id
            }), 400

        card_number = cryptogram_data.get('hpan')
        exp_date = cryptogram_data.get('expDate')
        cvc = cryptogram_data.get('cvc')

        if not all([card_number, exp_date, cvc]):
            return jsonify({
                "code": 400,
                "message": "Bad Request: Missing required fields in cryptogram (hpan, expDate, cvc).",
                "invoiceId": invoice_id,
                "id": "",
                "reference": "",
                "accountId": account_id
            }), 400

        # Проверка карты на ее наличие в словаре таковых с ошибками и их ошибки
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

        # Генерация случайных значений для ключей, в которых это позволительно
        transaction_id = str(uuid.uuid4())
        reference = ''.join(random.choices('0123456789', k=12))
        int_reference = uuid.uuid4().hex.upper()[:16]
        approval_code = ''.join(random.choices('0123456789', k=6))
        card_id = str(uuid.uuid4())

        # Успешный ответ
        response_data = {
            "id": transaction_id,
            "accountId": account_id,
            "amount": amount,
            "amountBonus": 0,
            "currency": currency,
            "description": request_data.get('description'),
            "email": request_data.get('email'),
            "invoiceID": invoice_id,
            "language": "rus",
            "phone": request_data.get('phone'),
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
            "ipCity": "",
            "ipCountry": "",
            "ipDistrict": "",
            "ipLatitude": 0,
            "ipLongitude": 0,
            "ipRegion": "",
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

def init_app(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(payment_bp)