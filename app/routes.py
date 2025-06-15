from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session
from app.schemas import CryptopayRequestSchema, CryptogramSchema
from app.services import (
    create_transaction, charge_transaction,
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
            cryptogram_str = validated_data['cryptogram']
            cryptogram_data = cryptogram_schema.loads(cryptogram_str)
            hpan = cryptogram_data['hpan']  # Получаем hpan из криптограммы
            exp_date = cryptogram_data['expDate']
            cvc = cryptogram_data.get('cvc')
            terminal_id = cryptogram_data.get('terminalId')
        except (json.JSONDecodeError, ValidationError) as err:
            current_app.logger.warning(f"Ошибка десериализации/валидации криптограммы: {err}")
            return jsonify({
                "code": 400, "message": "Bad Request: Invalid cryptogram format or content.",
                "errors": str(err), "invoiceId": validated_data['invoiceId'],
                "id": "", "reference": "", "accountId": validated_data.get('accountId')
            }), 400

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
        request_data = request.get_json()
        charge_amount = None
        if request_data and 'amount' in request_data:
            try:
                charge_amount = decimal.Decimal(str(request_data['amount'])).quantize(decimal.Decimal('0.01'))
            except (ValueError, decimal.InvalidOperation):
                return jsonify({"error": "Некорректный формат суммы"}), 400

        updated_transaction = charge_transaction(db_session, transaction_id, charge_amount)

        account_balance_record = db_session.query(AccountBalance).filter_by(
            account_id=updated_transaction.account_id).first()
        remaining_authorized_balance = str(
            account_balance_record.authorized_balance) if account_balance_record else "0.00"

        return jsonify({
            "message": "Средства успешно списаны.",
            "transaction_id": str(updated_transaction.id),
            "invoice_id": updated_transaction.invoice_id,
            "status": updated_transaction.status,
            "charged_amount": str(charge_amount if charge_amount is not None else updated_transaction.amount),
            "remaining_authorized_balance": remaining_authorized_balance
        }), 200

    except Exception as e:
        current_app.logger.error(f"Ошибка при списании средств для транзакции {transaction_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400