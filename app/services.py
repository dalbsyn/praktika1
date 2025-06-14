from app.models import Transaction  # Импортируем модель
from datetime import datetime, timezone
import uuid
import random


def create_transaction(db_session, validated_data, cryptogram_data):
    """
    Создает и сохраняет новую транзакцию в базе данных

    :param db_session: Сессия SQLAlchemy для работы с базой данных.
    :param validated_data: Валидированные данные запроса Cryptopay.
    :param cryptogram_data: Десериализованные данные криптограммы.
    :return: Объект Transaction, представляющий сохраненную транзакцию.
    """

    # Разбор валидированных данных из запроса
    amount = validated_data['amount']
    currency = validated_data['currency']
    name = validated_data['name']
    invoice_id = validated_data['invoiceId']
    invoice_id_alt = validated_data.get('invoiceIdAlt')
    description = validated_data['description']
    post_link = validated_data['postLink']
    failure_post_link = validated_data.get('failurePostLink')
    card_save = validated_data['cardSave']
    account_id = validated_data.get('accountId')
    email = validated_data.get('email')
    phone = validated_data.get('phone')
    data = validated_data.get('data')

    # Разбор данных криптограммы
    hpan = cryptogram_data['hpan']
    exp_date = cryptogram_data['expDate']
    cvc = cryptogram_data.get('cvc')
    terminal_id = cryptogram_data.get('terminalId')

    # Генерируем уникальные референсы и код одобрения
    reference = f"REF-{str(uuid.uuid4()).split('-')[0]}"
    int_reference = f"INTREF-{str(uuid.uuid4()).split('-')[0]}"
    approval_code = ''.join(random.choices('0123456789', k=6))

    # Определяем статус транзакции
    # Пока что всегда "удержание" (AUTH)
    transaction_status = "AUTH"

    # Создаем новый объект транзакции
    new_transaction = Transaction(
        invoice_id=invoice_id,
        invoice_id_alt=invoice_id_alt,
        amount=amount,
        currency=currency,
        hpan=hpan,
        exp_date=exp_date,
        cvc=cvc,
        status=transaction_status,
        name=name,
        description=description,
        account_id=account_id,
        email=email,
        phone=phone,
        post_link=post_link,
        failure_post_link=failure_post_link,
        card_save=card_save,
        data=data,
        terminal_id=terminal_id,
        reference=reference,
        int_reference=int_reference,
        approval_code=approval_code,
        card_id=f"card_{str(uuid.uuid4()).split('-')[0]}",  # Эмулируем cardId
    )

    # Добавляем транзакцию в сессию и фиксируем
    db_session.add(new_transaction)
    db_session.commit()

    # Возвращаем созданный объект транзакции (он теперь содержит ID из БД)
    return new_transaction