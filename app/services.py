from app.models import Transaction, AccountBalance
import uuid
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func


def create_transaction(db_session, validated_data, cryptogram_data):
    """
    Создает новую транзакцию со статусом AUTH и соответствующим образом
    обновляет AccountBalance.
    """

    # Генерация int_reference (теперь String(255))
    int_reference = str(uuid.uuid4()).replace('-',
                                              '')  # Убираем '-' для соответствия string-представлению, но длина важна
    if len(int_reference) > 255:  # Убедимся, что не превышаем длину
        int_reference = int_reference[:255]

    # Генерация approval_code (String(6))
    approval_code = str(uuid.uuid4().int)[:6]

    # Генерация card_id (UUID) - schema уже даст нам объект UUID, но если его нет, генерируем
    card_id = validated_data.get('cardId', uuid.uuid4())  # cardId теперь может приходить из запроса или генерироваться

    # Status (String(50))
    transaction_status = "AUTH"

    # Создание новой записи транзакции
    new_transaction = Transaction(
        # Поля, пришедшие из валидированных данных запроса
        invoice_id=validated_data['invoiceId'],
        invoice_id_alt=validated_data.get('invoiceIdAlt'),
        amount=validated_data['amount'],
        currency=validated_data['currency'],
        name=validated_data['name'],
        description=validated_data['description'],
        account_id=validated_data.get('accountId', uuid.uuid4()),
        email=validated_data.get('email'),
        phone=validated_data.get('phone'),
        post_link=validated_data['postLink'],
        failure_post_link=validated_data.get('failurePostLink'),
        card_save=validated_data['cardSave'],
        data=validated_data.get('data'),

        # Поля из криптограммы
        hpan=cryptogram_data['hpan'],
        exp_date=cryptogram_data['expDate'],
        cvc=cryptogram_data.get('cvc'),
        terminal_id=cryptogram_data.get('terminalId', uuid.uuid4()),

        # Сгенерированные или фиксированные эмулятором поля
        int_reference=int_reference,
        approval_code=approval_code,
        card_id=card_id,
        status=transaction_status
    )

    db_session.add(new_transaction)
    db_session.flush()  # flush, чтобы получить ID новой транзакции до коммита

    # Агрегирование суммы удерживаемых средств по account_id
    amount_to_add = new_transaction.amount

    stmt = insert(AccountBalance).values(
        account_id=new_transaction.account_id,
        authorized_balance=amount_to_add,
        updated_at=func.now()
    ).on_conflict_do_update(
        # Указываем первичный ключ для обнаружения конфликта
        index_elements=[AccountBalance.account_id],
        set_={'authorized_balance': AccountBalance.authorized_balance + amount_to_add,
              'updated_at': func.now()}
    )
    db_session.execute(stmt)

    db_session.commit()
    db_session.refresh(new_transaction)

    return new_transaction
