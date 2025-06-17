from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session
from app.schemas import CryptopayRequestSchema, CryptogramSchema
from app.services import (
    create_transaction, charge_transaction, cancel_transaction, refund_transaction
)
from marshmallow import ValidationError
import json
import uuid
import decimal
from app.exceptions import CardError

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

    db_session = current_app.extensions['sqlalchemy_session']()

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
        invoice_id = validated_data['invoiceId']
        validated_data.get('invoiceIdAlt')
        account_id = validated_data.get('accountId')
        validated_data.get('email')
        validated_data.get('phone')
        validated_data.get('failurePostLink')
        data_str = validated_data.get('data')

        # Считывание и валидация содержимого криптограммы
        try:
            cryptogram_str = validated_data['cryptogram']
            cryptogram_data = cryptogram_schema.loads(cryptogram_str)
            hpan = cryptogram_data['hpan']
            cryptogram_data.get('cvc')
            cryptogram_data.get('terminalId')
        except (json.JSONDecodeError, ValidationError) as err:
            current_app.logger.warning(f"Ошибка десериализации/валидации криптограммы: {err}")
            return jsonify({
                "code": 400, "message": "Bad Request: Invalid cryptogram format or content.",
                "errors": str(err), "invoiceId": validated_data['invoiceId'],
                "id": "", "reference": "", "accountId": validated_data.get('accountId')
            }), 400

        # Считывание data на то, что он является JSON
        if data_str:
            try:
                json.loads(data_str)
            except json.JSONDecodeError:
                return jsonify({
                    "code": 400,
                    "message": "Bad Request: Invalid 'data' format (must be a JSON string).",
                    "invoiceId": invoice_id, "id": "", "reference": "", "accountId": account_id
                }), 400

        # Проверка номера карты на его наличие в списке таковых с ошибками
        error_config_for_card = current_app.config['ERROR_CARD_NUMBERS'].get(hpan)

        if error_config_for_card is not None:
            # Попытка найти ошибку для операции 'auth', если нет - 'default'
            error_code_key_for_card = error_config_for_card.get('auth') or error_config_for_card.get('default')

            if error_code_key_for_card is not None:
                error_code = error_code_key_for_card
                error_message = current_app.config['EPAY_ERROR_CODES'].get(error_code_key_for_card,
                                                                           "Неизвестная ошибка.")

                # Если код 0 (успех), возвращаем 200, иначе 400
                status_code = 200 if error_code == 0 else 400

                # Если это не успех, генерируем новый ID транзакции для ответа об ошибке
                response_id = str(uuid.uuid4()) if error_code != 0 else ""

                # Специальная обработка для успеха, чтобы эмулятор выдал success-поля
                if error_code == 0:
                    # Создаем успешную транзакцию, если карта настроена на успех
                    new_transaction = create_transaction(db_session, validated_data, cryptogram_data)
                    response_id = str(new_transaction.id)
                    # Формируем успешный ответ, как будто транзакция прошла
                    return jsonify({
                        "id": response_id,
                        "accountId": validated_data.get('accountId', ''),
                        "amount": float(new_transaction.amount),
                        "amountBonus": 0,
                        "currency": new_transaction.currency,
                        "description": new_transaction.description,
                        "email": new_transaction.email,
                        "invoiceID": new_transaction.invoice_id,
                        "language": "rus",
                        "phone": new_transaction.phone,
                        "reference": new_transaction.reference,
                        "intReference": new_transaction.int_reference,
                        "secure3D": None,
                        "cardID": new_transaction.card_id,
                        "fee": 0,
                        "approvalCode": new_transaction.approval_code,
                        "code": 0,
                        "status": new_transaction.status,
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
                    }), 200
                else:
                    # Возвращаем ошибку, если карта настроена на ошибку
                    return jsonify({
                        "code": error_code,
                        "message": error_message,
                        "invoiceId": validated_data['invoiceId'],
                        "id": response_id,
                        "reference": "",
                        "accountId": validated_data.get('accountId')
                    }), status_code

        new_transaction = create_transaction(db_session, validated_data, cryptogram_data)

        # Успешный ответ
        response_data = {
            "id": str(new_transaction.id),
            "accountId": validated_data.get('accountId', ''),
            "amount": float(new_transaction.amount),
            "amountBonus": 0,
            "currency": new_transaction.currency,
            "description": new_transaction.description,
            "email": new_transaction.email,
            "invoiceID": new_transaction.invoice_id,
            "language": "rus",
            "phone": new_transaction.phone,
            "reference": new_transaction.reference,
            "intReference": new_transaction.int_reference,
            "secure3D": None,
            "cardID": new_transaction.card_id,
            "fee": 0,
            "approvalCode": new_transaction.approval_code,
            "code": 0,
            "status": new_transaction.status,
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
        # Другая ошибка
        return jsonify({"code": 999, "message": f"Internal Server Error: {str(e)}",
        }), 500


@payment_bp.route('/<uuid:transaction_id>/charge', methods=['POST'])
def charge_operation(transaction_id: uuid.UUID):
    """
    Эндпоинт для снятия средств.

    :param transaction_id: UUID транзакции, которая находится в состоянии AUTH. Можно получить из ответа на выполнение запроса платежа.
    :return: json-ответ
    """
    db_session: Session = current_app.extensions['sqlalchemy_session']()

    try:
        # Получение данных из JSON-запроса. Если JSON нет, то считывание из URL
        request_data_json = request.get_json(silent=True)

        charge_amount = None

        # JSON или параметры URL
        if request_data_json:
            current_app.logger.debug(f"Получены данные из JSON для charge: {request_data_json}")
            data_source = request_data_json
        else:
            current_app.logger.debug(f"Получены данные из URL args для charge: {request.args}")
            data_source = request.args

        # Считывание суммы
        if 'amount' in data_source:
            try:
                charge_amount = decimal.Decimal(str(data_source['amount'])).quantize(decimal.Decimal('0.01'))
            except (ValueError, decimal.InvalidOperation):
                return jsonify({"error": "Некорректный формат суммы."}), 400

        charge_transaction(db_session, transaction_id, charge_amount)

        return jsonify({
        }), 200

    except CardError as ee:
        return jsonify({
            "code": ee.code,
            "message": ee.message,
        }), 400

    except Exception as e:
        # Другая ошибка
        return jsonify({"code": 999, "message": str(e)}), 500


@payment_bp.route('/<uuid:transaction_id>/cancel', methods=['POST'])
def cancel_operation(transaction_id: uuid.UUID):
    db_session: Session = current_app.extensions['sqlalchemy_session']()

    try:
        # Выполнение отмены платежа
        cancel_transaction(db_session, transaction_id)
        return "", 200

    except CardError as ee:
        current_app.logger.warning(f"Ошибка Epay при отмене для транзакции {transaction_id}: {ee.message}")
        return jsonify({
            "code": ee.code,
            "message": ee.message,
        }), 400


@payment_bp.route('/<uuid:transaction_id>/refund', methods=['POST'])
def refund_operation(transaction_id: uuid.UUID):
    db_session: Session = current_app.extensions['sqlalchemy_session']()

    try:
        # Получение данных из JSON-запроса. Если JSON нет, то считывание из URL
        request_data_json = request.get_json(silent=True)
        refund_amount = None

        # JSON или параметры URL
        if request_data_json:
            data_source = request_data_json
        else:  # Нет JSON-данных, пробуем параметры URL
            data_source = request.args

        # Получение externalID
        external_id = data_source.get('externalID')

        # Считывание amount
        if 'amount' in data_source:
            try:
                refund_amount = decimal.Decimal(str(data_source['amount'])).quantize(decimal.Decimal('0.01'))
            except (ValueError, decimal.InvalidOperation):
                return jsonify({"code": 100, "message": "Некорректный формат суммы."}), 400

        # Валидация externalID, независимо от источника
        if not external_id:
            raise Exception("Параметр 'externalID' является обязательным.")
        if not isinstance(external_id, str) or len(external_id) != 22:
            raise Exception("Параметр 'externalID' должен быть строкой длиной 22 символа.")

        refund_transaction(db_session, transaction_id, refund_amount, external_id)

        return "", 200

    except CardError as ee:
        return jsonify({
            "code": ee.code,
            "message": ee.message,
        }), 400

    except Exception as e:
        # Другая ошибка
        return jsonify({"code": 999, "message": str(e)}), 400
