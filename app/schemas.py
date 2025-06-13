from marshmallow import Schema, fields, validate, ValidationError
import re
from decimal import Decimal
from app.config import VALIDATION_REQUIRE_TLD_FOR_URLS

"""
Сперва определяются сторонние валидаторы, которые используют обычные регулярные
выражения.
Затем, средствами marshmallow проверяются другие значения. Логика работы 
несложная. 
"""

# Валидатор для номера карты (hpan)
def validate_hpan(hpan):
    amount = 16
    if not re.fullmatch(rf'^\d{{{amount}}}$', hpan):
        raise ValidationError(f'hPAN (хэш-пан) должен содержать строго из {amount} цифр.')


# Валидатор для срока действия карты (expDate)
def validate_exp_date(exp_date):
    amount = 4
    if not re.fullmatch(rf'^\d{{{amount}}}$', exp_date):
        raise ValidationError(f'Дата срока действия карты должна состоять из {amount} цифр формата (ММГГ).')


# Валидатор для CVC
def validate_cvc(cvc):
    amount = 3
    if not re.fullmatch(rf'^\d{{{amount}}}$', cvc):
        raise ValidationError(f'CVC должен состоять из {amount} цифр.')


# Схема для криптограммы
class CryptogramSchema(Schema):
    hpan = fields.String(required=True, validate=validate_hpan,
                         metadata={"description": "Номер карты (хешированный или токенизированный)"})
    expDate = fields.String(required=True, validate=validate_exp_date,
                            metadata={"description": "Срок действия карты (MMYY)"})
    cvc = fields.String(required=True, validate=validate_cvc,
                        metadata={"description": "CVV/CVC код карты"})
    terminalId = fields.String(required=False,
                               metadata={"description": "Идентификатор терминала"})  # Необязательное поле


# Схема для входящего запроса Cryptopay
class CryptopayRequestSchema(Schema):
    postLink = fields.URL(required=True, require_tld=VALIDATION_REQUIRE_TLD_FOR_URLS,
                          metadata={"description": "Ссылка для отправки результата авторизации"})
    failurePostLink = fields.URL(required=False, require_tld=VALIDATION_REQUIRE_TLD_FOR_URLS,
                                 metadata={"description": "Ссылка для отправки неудачного результата авторизации"})
    amount = fields.Decimal(required=True, validate=validate.Range(min=Decimal('0.01')),
                            metadata={"description": "Сумма платежа"})
    currency = fields.String(required=True, validate=validate.Length(min=3, max=3),
                             metadata={"description": "Сокращенная валюта, типа: KZT)"})
    name = fields.String(required=True, validate=validate.Length(min=1),
                         metadata={"description": "Имя держателя карты"})
    cryptogram = fields.String(required=True,
                               metadata={"description": "Зашифрованные параметры платежной карты (JSON строка)"})
    invoiceId = fields.String(required=True,
                              validate=validate.Regexp(r'^\d{6,15}$', error='Номер заказа должен состоять из числа, состоящий из цифр в количестве от 6 до 15..'),
                              metadata={"description": "Номер заказа, генерируется коммерсантом"})
    invoiceIdAlt = fields.String(required=False,
                                 validate=validate.Regexp(r'^\d{6,15}$', error='Альтернативный номер заказа должен состоять из числа, состоящий из цифр в количестве от 6 до 15.'),
                                 metadata={"description": "Альтернативный номер заказа"})
    description = fields.String(required=True, validate=validate.Length(min=1),
                                metadata={"description": "Информация о товарах или услугах"})
    accountId = fields.String(required=False,
                              metadata={"description": "Идентификатор клиента в системе коммерсанта"})
    email = fields.Email(required=False,
                         metadata={"description": "Email клиента"})
    phone = fields.String(required=False,
                          validate=validate.Regexp(r'^\d{7,15}$', error='Phone number must be 7 to 15 digits.'),
                          metadata={"description": "Телефон клиента"})
    cardSave = fields.Boolean(required=True,
                              metadata={"description": "Параметр сохранения карты (true/false)"})
    data = fields.String(required=False,
                         metadata={"description": "Дополнительное поле (JSON строка)"})