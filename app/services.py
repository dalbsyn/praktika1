from datetime import datetime
from sqlalchemy.orm import Session
from app.db_session import get_db
from app.database.accounts import Accounts
from app.database.transactions import Transactions

def get_welcome_message():
    return "test"

def get_example_data():
    return {'item1': 'Значение 1', 'item2': 'Значение 2', 'status': 'успешно'}

def process_hold_funds(operation_id: str, account_identifier: str, amount: float, description: str):
    '''
    Реализация удержания средств на счету

    Входные аргументы:
    - `operation_id` - идентификатор операции, полученная из URL;
    - `account_identifer` - идентификатор аккаунта в формате UUID версии 4;
    - `amount` - сумма средств для удержания. Принимает целочисленные (int) и числа с плавающей точкой (float);
    - `description` - описание удержания.

    Выходные данные - JSON-ответ:

    ```
    {
        "account_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "amount": 100,
        "message": "Описание удержания",
        "operation_id": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY",
        "status": "PENDING"
    }
    ```

    Ошибки:
    - `ValueError`:
        - счета не существует;
        - недостаточно средств;
        - операция уже существует.
    '''

    if amount <= 0:
        raise ValueError("Сумма удержания должна быть положительной.")

    db: Session = next(get_db())
    try:
        '''
        Проверка уникальности operation_id и поиск незавершенной или отмененной транзакции с этим же идентификатором.
        
        Реализована через извлечение идентификаторов транзакций и сравнение, а затем проверку типов и статусов транзакций.
        '''

        existing_hold_transaction = db.query(Transactions).filter(
            Transactions.transaction_id == operation_id,
            Transactions.transaction_type == 'HOLD',
            Transactions.transaction_status.in_(['PENDING', 'HELD']) 
        ).first()

        if existing_hold_transaction:
            '''
            Возвращение информации об операции с существующим идентификатором, если проверка выше выполняется.
            '''

            return {
                "operation_id": existing_hold_transaction.transaction_id,
                "account_id": existing_hold_transaction.account_id,
                "amount": float(existing_hold_transaction.amount),
                "status": existing_hold_transaction.transaction_status,
                "message": "Операция удержания с данным ID уже существует и активна."
            }

        '''
        Проверка на существование аккаунта с предоставленным идентификатором.

        Ошибка, если аккаунта не существует.
        '''
        account = db.query(Accounts).filter(
            Accounts.account_number == account_identifier
        ).first()

        if not account:
            raise ValueError(f"Счет с номером '{account_identifier}' не найден.")

        '''
        Проверка баланса - если баланса меньше, чем запрашивается, то ошибка. 
        
        Ошибка выводит доступный баланс и запрошенный баланс для удержания. 
        '''

        available_balance = float(account.balance) - float(account.held_balance)
        if available_balance < amount:
            raise ValueError(f"Недостаточно средств на счету {account.account_number}. Доступно: {available_balance}, запрошено: {amount}.")

        '''
        Реализация транзакции - по умолчанию устанавливается статус PENDING
        '''
        new_transaction = Transactions(
            transaction_id=operation_id,
            account_id=account.id,
            transaction_type='HOLD',
            transaction_date=datetime.utcnow(),
            amount=amount,
            description=description,
            transaction_status='PENDING'
        )
        db.add(new_transaction)

        '''
        Расчет удерживаемого баланса на счету
        '''
        
        account.held_balance = float(account.held_balance) + amount

        db.commit()
        db.refresh(new_transaction)

        '''
        Ответ для успешного запроса
        '''

        return {
            "operation_id": new_transaction.transaction_id,
            "account_id": account.account_number,
            "amount": float(new_transaction.amount),
            "status": new_transaction.transaction_status,
            "message": "Средства успешно удержаны."
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()