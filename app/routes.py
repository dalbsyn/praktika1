from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session
from app.schemas import CryptopayRequestSchema, CryptogramSchema
from app.services import (
    create_transaction, charge_transaction, cancel_transaction, refund_transaction
)
from marshmallow import ValidationError, fields
import json
import uuid
import decimal

from app.models.account_balance import AccountBalance

# Инициализация Blueprint
main_bp = Blueprint('main', __name__)
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

class ChargeRequestSchema(CryptopayRequestSchema):
    amount = fields.Decimal(required=False, as_string=False, places=2, load_default=None,
                            metadata={'description': 'Сумма для списания. Если не указана, списывается вся сумма транзакции.'})

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
            hpan = cryptogram_data['hpan']  # Получаем hpan из криптограммы
            cryptogram_data.get('cvc')
            cryptogram_data.get('terminalId')
        except (json.JSONDecodeError, ValidationError) as err:
            current_app.logger.warning(f"Ошибка десериализации/валидации криптограммы: {err}")
            return jsonify({
                "code": 400, "message": "Bad Request: Invalid cryptogram format or content.",
                "errors": str(err), "invoiceId": validated_data['invoiceId'],
                "id": "", "reference": "", "accountId": validated_data.get('accountId')
            }), 400

        # Считывание data, если оно есть
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
        error_code_key_for_card = None
        # Проверяем, есть ли hpan в наших "ошибочных" номерах
        if hpan in current_app.config['ERROR_CARD_NUMBERS']:
            error_code_key_for_card = current_app.config['ERROR_CARD_NUMBERS'][hpan]

        if error_code_key_for_card is not None:
            # Получаем код и сообщение об ошибке из EPAY_ERROR_CODES
            error_code = error_code_key_for_card
            error_message = current_app.config['EPAY_ERROR_CODES'].get(error_code_key_for_card)

            # Если код не найден, используем общий, но это маловероятно, если EPAY_ERROR_CODES настроен верно.
            if error_code is None:
                error_code = current_app.config['EPAY_ERROR_CODES'].get("general_system_error", 9999)
                error_message = "Transaction failed: Unknown error code for card."

            # Возвращаем ошибку без сохранения в БД
            return jsonify({
                "code": error_code,
                "message": error_message,
                "invoiceId": validated_data['invoiceId'],
                "id": str(uuid.uuid4()),  # Генерируем новый ID для ответа об ошибке
                "reference": "",
                "accountId": validated_data.get('accountId')
            }), 400

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
        return jsonify({
            "code": 500,
            "message": f"Internal Server Error: {str(e)}",
            "id": "",
            "reference": "",
            "accountId": ""
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

        updated_transaction = charge_transaction(db_session, transaction_id, charge_amount)

        account_balance_record = db_session.query(AccountBalance).filter_by(
            account_id=updated_transaction.account_id).first()
        remaining_authorized_balance = str(account_balance_record.authorized_balance) if account_balance_record else "0.00"

        return jsonify({
        }), 200
    except Exception as e:
        # Заглушка ошибки для соответсвия таковму из EPAY
        return jsonify({"error": str(e)}), 400

@payment_bp.route('/<uuid:transaction_id>/cancel', methods=['POST'])
def cancel_operation(transaction_id: uuid.UUID):
    db_session: Session = current_app.extensions['sqlalchemy_session']()

    try:
        # Выполнение отмены платежа
        cancel_transaction(db_session, transaction_id)
        return "", 200

    except Exception as e:
        # Заглушка ошибки для соответсвия таковму из EPAY
        return jsonify({"code": 100, "message": str(e)}), 400


@payment_bp.route('/<uuid:transaction_id>/refund', methods=['POST'])
def refund_operation(transaction_id: uuid.UUID):
    db_session: Session = current_app.extensions['sqlalchemy_session']()

    try:
        # Получение данных из JSON-запроса. Если JSON нет, то считывание из URL
        request_data_json = request.get_json(silent=True)

        external_id = None
        refund_amount = None

        # JSON или параметры URL
        if request_data_json:
            current_app.logger.debug(f"Получены данные из JSON для refund: {request_data_json}")
            data_source = request_data_json
        else:  # Нет JSON-данных, пробуем параметры URL
            current_app.logger.debug(f"Получены данные из URL args для refund: {request.args}")
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

        updated_transaction = refund_transaction(db_session, transaction_id, refund_amount, external_id)

        return "", 200

    except Exception as e:
        current_app.logger.error(f"Ошибка при возврате средств для транзакции {transaction_id}: {e}", exc_info=True)
        # Заглушка ошибки для соответсвия таковму из EPAY
        return jsonify({"code": 100, "message": str(e)}), 400
