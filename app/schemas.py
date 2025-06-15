from marshmallow import Schema, fields, pre_load, ValidationError
from marshmallow.validate import Length, Range
import uuid
import json

"""
Сперва определяются сторонние валидаторы, которые используют обычные регулярные
выражения.
Затем, средствами marshmallow проверяются другие значения. Логика работы 
несложная. 
"""

class CryptogramSchema(Schema):
    hpan = fields.String(required=True, validate=Length(equal=16),
                         metadata={'description': 'Хешированный номер карты (16 цифр)'})
    expDate = fields.String(required=True, validate=Length(equal=4),
                            metadata={'description': 'Срок действия карты (ММГГ)'})
    cvc = fields.String(validate=Length(min=3, max=4), load_default=None,
                        metadata={'description': 'CVC/CVV карты (3 или 4 цифры)'})
    terminalId = fields.UUID(load_default=None,
                             metadata={'description': 'Идентификатор терминала (UUID)'})  # Изменен на fields.UUID

    @pre_load
    def process_terminal_id(self, data, **kwargs):
        if 'terminalId' in data and data['terminalId'] is not None:
            # Преобразуем строковый terminalId в объект UUID
            try:
                data['terminalId'] = uuid.UUID(data['terminalId'])
            except ValueError:
                # Если это не валидный UUID, Marshmallow выдаст ошибку валидации
                # fields.UUID сам умеет это обрабатывать, так что можно просто пропустить.
                # Но если вы хотите более кастомное сообщение, можно добавить здесь.
                pass
        return data


class CryptopayRequestSchema(Schema):
    invoiceId = fields.String(required=True, validate=Length(max=15),
                              metadata={'description': 'ID инвойса (до 15 символов)'})
    invoiceIdAlt = fields.String(validate=Length(max=15), load_default=None,
                                 metadata={'description': 'Альтернативный ID инвойса (до 15 символов)'})  # Новое поле
    amount = fields.Decimal(required=True, as_string=False, places=2,
                            validate=Range(min=0.01),
                            metadata={'description': 'Сумма платежа (DECIMAL)'})  # Изменен на fields.Decimal
    currency = fields.String(required=True, validate=Length(equal=3),
                             metadata={'description': 'Валюта платежа (3 символа, например KZT)'})
    name = fields.String(required=True, validate=Length(max=255),
                         metadata={'description': 'Имя плательщика (до 255 символов)'})  # Новое поле
    description = fields.String(required=True, validate=Length(max=65535),  # TEXT обычно до 65535 байт
                                metadata={
                                    'description': 'Описание платежа (TEXT)'})  # Изменен на String с большей длиной
    accountId = fields.UUID(load_default=None,
                            metadata={'description': 'ID аккаунта (UUID)'})  # Изменен на fields.UUID
    email = fields.Email(validate=Length(max=255), load_default=None,
                         metadata={'description': 'Email плательщика (до 255 символов)'})
    phone = fields.String(validate=Length(max=15), load_default=None,
                          metadata={'description': 'Телефон плательщика (до 15 символов)'})
    postLink = fields.String(required=True, validate=Length(max=2048),
                             metadata={'description': 'URL для POST-уведомления (до 2048 символов)'})  # Новое поле
    failurePostLink = fields.String(validate=Length(max=2048), load_default=None,
                                    metadata={
                                        'description': 'URL для POST-уведомления о неудаче (до 2048 символов)'})  # Новое поле
    cardSave = fields.Boolean(required=True,
                              metadata={'description': 'Сохранять ли карту (Boolean)'})  # Новое поле
    data = fields.String(validate=Length(max=65535), load_default=None,
                         metadata={'description': 'Дополнительные данные (TEXT)'})  # Новое поле
    cryptogram = fields.String(required=True,  # Валидируется как JSON-строка в pre_load
                               metadata={'description': 'Зашифрованные данные карты в JSON-строке'})

    # Валидация криптограммы как JSON-строки
    @pre_load
    def validate_cryptogram_json(self, data, **kwargs):
        if 'cryptogram' in data and isinstance(data['cryptogram'], str):
            try:
                # Попытка загрузить криптограмму как JSON, чтобы убедиться, что она корректна
                json.loads(data['cryptogram'])
            except json.JSONDecodeError:
                raise ValidationError("Cryptogram must be a valid JSON string.", field_name="cryptogram")

        # Преобразуем строковые UUID в объекты UUID для accountId
        if 'accountId' in data and data['accountId'] is not None:
            try:
                data['accountId'] = uuid.UUID(data['accountId'])
            except ValueError:
                pass  # fields.UUID сам обработает ошибку валидации

        return data