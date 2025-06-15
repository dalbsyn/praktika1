import uuid
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, and_
from app.models.transaction import Transaction
from app.models.account_balance import AccountBalance
from datetime import datetime, timezone
from sqlalchemy.orm.session import Session
import decimal


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


def charge_transaction(db_session: Session, transaction_id: uuid.UUID, charge_amount: float = None):
    """
    Списывает (подтверждает) средства для авторизованной транзакции.
    Если charge_amount не указан, списывается полная авторизованная сумма транзакции.

    Аргументы:
        db_session: Сессия базы данных.
        transaction_id: UUID транзакции, которая должна быть списана.
        charge_amount: Опциональная сумма для списания. Если None, списывается вся авторизованная сумма.
    """
    try:
        transaction = db_session.query(Transaction).filter_by(id=transaction_id).first()

        if not transaction:
            raise Exception(f"Транзакция с ID {transaction_id} не найдена.")

        if transaction.status != "AUTH":
            raise Exception(
                f"Транзакция ID {transaction_id} находится в статусе '{transaction.status}', ожидается 'AUTH'.")

        amount_to_charge = transaction.amount if charge_amount is None else charge_amount

        amount_to_charge = decimal.Decimal(str(amount_to_charge)).quantize(decimal.Decimal('0.01'))

        if amount_to_charge <= 0:
            raise Exception("Сумма списания должна быть положительной.")

        if amount_to_charge > transaction.amount:
            raise Exception(
                f"Запрошенная сумма {amount_to_charge} {transaction.currency} превышает авторизованную сумму {transaction.amount} {transaction.currency} для транзакции ID {transaction_id}."
            )

        transaction.status = "CHARGE"
        transaction.updated_at = datetime.now(timezone.utc)

        db_session.query(AccountBalance).filter(AccountBalance.account_id == transaction.account_id).update(
            {
                AccountBalance.authorized_balance: AccountBalance.authorized_balance - amount_to_charge,
                AccountBalance.updated_at: func.now()
            },
            synchronize_session='fetch'
        )

        db_session.execute(
            AccountBalance.__table__.update().
            where(and_(
                AccountBalance.account_id == transaction.account_id,
                AccountBalance.authorized_balance < 0
            )).
            values(authorized_balance=0, updated_at=func.now())
        )

        db_session.commit()
        db_session.refresh(transaction)

        return transaction

    except Exception as e:
        db_session.rollback()
        raise Exception(f"Ошибка списания средств: {e}")


def cancel_transaction(db_session: Session, transaction_id: uuid.UUID):
    """
    Отмена оплаты.
    Передаваемая транзакция должна находиться строго в состоянии AUTH.

    :param db_session: сессия базы данных
    :param transaction_id: идентификатор транзакции
    :return: json-ответ
    """
    try:
        transaction = db_session.query(Transaction).filter_by(id=transaction_id).first()

        if not transaction:
            raise Exception(f"Транзакция с ID {transaction_id} не найдена.")

        # Проверка транзакции на соответствие состоянию AUTH
        if transaction.status != "AUTH":
            raise Exception(
                f"Транзакция ID {transaction_id} находится в статусе '{transaction.status}', ожидается 'AUTH' для отмены.")

        # Обновление состоянис транзакции на CANCELLED
        transaction.status = "CANCEL"
        transaction.updated_at = datetime.now(timezone.utc)

        # Снятие с удержания уже закрытых средств
        amount_to_release = transaction.amount

        db_session.query(AccountBalance).filter(AccountBalance.account_id == transaction.account_id).update(
            {
                AccountBalance.authorized_balance: AccountBalance.authorized_balance - amount_to_release,
                AccountBalance.updated_at: func.now()
            },
            synchronize_session='fetch'
        )

        # Если по какой-то причине сумма аккаунта окажется ниже 0, то пусть будет 0
        db_session.execute(
            AccountBalance.__table__.update().
            where(and_(
                AccountBalance.account_id == transaction.account_id,
                AccountBalance.authorized_balance < 0
            )).
            values(authorized_balance=0, updated_at=func.now())
        )

        db_session.commit()
        db_session.refresh(transaction)
        return transaction

    except Exception as e:
        db_session.rollback()
        raise Exception(f"Ошибка при отмене транзакции: {e}")


def refund_transaction(db_session: Session, transaction_id: uuid.UUID, refund_amount: float = None,
                       external_id: str = None):
    """
    Возврат средств.
    Передаваемая транзакция должна быть со статусом CHARGE.
    Возвращаемые средства вернутся на какой-то счет пользователя, а не в удерживаемую сумму (которая хранится в базе
    данных). В базе данных счета пользователей не хранятся, так как не нужно. Средства возвращаются в никуда.

    :param db_session: сессия базы данных
    :param transaction_id: идентификатор транзакции
    :param refund_amount: опциональный - количество средств для возврата
    :param external_id: идентификатор коммерсанта
    :return: json-ответ
    """
    try:
        transaction = db_session.query(Transaction).filter_by(id=transaction_id).first()

        if not transaction:
            raise Exception(f"Транзакция с ID {transaction_id} не найдена.")

        # Проверка транзакции на соответствие статусу CHARGE
        if transaction.status != "CHARGE":
            raise Exception(
                f"Транзакция ID {transaction_id} находится в статусе '{transaction.status}', ожидается 'CHARGE' для возврата.")

        if not external_id or not isinstance(external_id, str) or len(external_id) != 22:
            raise Exception("Параметр 'externalID' является обязательным и должен быть строкой длиной 22 символа.")

        # Сумма для возврата
        amount_to_refund = transaction.amount if refund_amount is None else refund_amount

        amount_to_refund = decimal.Decimal(str(amount_to_refund)).quantize(decimal.Decimal('0.01'))

        if amount_to_refund <= 0:
            raise Exception("Сумма возврата должна быть положительной.")

        # Проверка того, что сумма возврата не превышает общую сумму транзакции
        if amount_to_refund > transaction.amount:
            raise Exception(
                f"Запрошенная сумма возврата {amount_to_refund} {transaction.currency} превышает общую сумму транзакции {transaction.amount} {transaction.currency} для транзакции ID {transaction_id}."
            )

        # Обновляем статус транзакции на REFUNDED
        transaction.status = "REFUNDED"
        transaction.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(transaction)

        return transaction

    except Exception as e:
        db_session.rollback()  # Откатываем изменения при любой ошибке
        raise Exception(f"Ошибка при возврате средств: {e}")