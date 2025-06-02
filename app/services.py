from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db_session import get_db
from app.database.accounts import Accounts
from app.database.transactions import Transactions
import uuid

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
            transaction_date=datetime.now(timezone.utc),
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

def process_charge_funds(operation_id: str):
    '''
    Реализация списания удержанных средств

    Входные аргументы:
    - `operation_id` - идентификатор операции, с которой надо списать средства.

    Выходные данные - JSON-ответ:

    ```
    {
        "operation_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "account_id": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY",
        "amount": 100,
        "status": "COMPLETED",
        "message": "Средства успешно списаны."
    }

    Ошибки:
    - ValueError:
        - транзакции не существует;
        - неверный внутренний статус транзакции - транзакция удержания средств должна быть в статусе PENDING;
        - недостаточно средств для списания.
    ```
    '''
   
    db: Session = next(get_db())
    try:
        '''
        Поиск исходной транзакции удержания по operation_id
        '''
        hold_transaction = db.query(Transactions).filter(
            Transactions.transaction_id == operation_id
        ).first()

        if not hold_transaction:
            raise ValueError(f"Транзакция удержания с ID '{operation_id}' не найдена.")

        '''
        Проверка типа и статуса транзакции

        Возвращает успешный ответ, если транзакция оказалась завершена:
        ```
        {
            "operation_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "account_id": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY",
            "amount": 100,
            "status": "COMPLETED",
            "message": "Средства по данной операции уже списаны."
        }
        ```
        Ошибка, если у типа транзакции стоит какой-то иной тип, отличный от удержания (HOLD).
        Ошибка, если у статуса транзакции стоит какой-то иной тип, отличный от ожиждания (PENDING).
        '''
        if hold_transaction.transaction_type != 'HOLD':
            raise ValueError(f"Транзакция с ID '{operation_id}' не является операцией удержания.")
        if hold_transaction.transaction_status == 'COMPLETED':
            return {
                "operation_id": hold_transaction.transaction_id,
                "account_id": hold_transaction.account_id,
                "amount": float(hold_transaction.amount),
                "status": hold_transaction.transaction_status,
                "message": "Средства по данной операции уже списаны."
            }
        if hold_transaction.transaction_status != 'PENDING':
            raise ValueError(f"Транзакция с ID '{operation_id}' имеет статус '{hold_transaction.transaction_status}', невозможно списать. Ожидается 'PENDING'.")

        '''
        Получение связанного счета с ранее полученной транзакцией
        '''
        account = db.query(Accounts).filter(
            Accounts.id == hold_transaction.account_id
        ).first()

        if not account:
            raise ValueError(f"Счет с ID '{hold_transaction.account_id}' для транзакции '{operation_id}' не найден.")

        '''
        Проверка достаточности удерживаемых средств
        '''
        amount_to_charge = float(hold_transaction.amount)
        if float(account.held_balance) < amount_to_charge:
            raise ValueError(f"Недостаточно удерживаемых средств на счету {account.account_number} для списания операции '{operation_id}'. Удержано: {float(account.held_balance)}, требуется: {amount_to_charge}.")

        '''
        Успешная транзакция добавляется в таблицу и обновляется значение средств с учетом списания средств
        '''
        hold_transaction.transaction_status = 'COMPLETED'
        hold_transaction.transaction_date = datetime.now(timezone.utc)

  
        account.held_balance = float(account.held_balance) - amount_to_charge
        account.balance = float(account.balance) - amount_to_charge

        db.commit()

        return {
            "operation_id": hold_transaction.transaction_id,
            "account_id": account.account_number,
            "amount": amount_to_charge,
            "status": hold_transaction.transaction_status,
            "message": "Средства успешно списаны."
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def process_cancel_hold(operation_id: str):
    '''
    Реализация отмены удерживаемых средств.

    Входные аргументы:
    - `operation_id` - идентификатор операции, которую надо отменить.

    Выходные данные - JSON-ответ:
    ```
    {
        "operation_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "account_id": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY",
        "amount": amount_to_return,
        "status": "CANCELLED",
        "message": "Удержание средств успешно отменено."
    }
    ```

    Ошибки:
    - ValueError:
        - транзакции не существует;
        - неверный внутренний статус транзакции - транзакция отмены удержания средств должна быть в статусе PENDING.
    '''

    db: Session = next(get_db())
    try:
        '''
        Поиск исходной транзакции удержания по operation_id
        '''
        hold_transaction = db.query(Transactions).filter(
            Transactions.transaction_id == operation_id
        ).first()


        '''
        Проверка типа и статуса транзакции

        Возвращает успешный ответ, если транзакция уже оказалась завершена:
        ```
        {
            "operation_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "account_id": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY",
            "amount": 100,
            "status": "CANCELLED",
            "message": "Средства по данной операции уже отменены."
        }
        ```

        Ошибка, если у типа транзакции стоит какой-то иной тип, отличный от удержания (HOLD).
        Ошибка, если у статуса транзакции стоит какой-то иной тип, отличный от ожиждания (PENDING).
        Ошибка, если у статуса транзакция уже завершена (CANCELLED).
        Ошибка, если средства уже списаны (COMPLETED).
        '''

        if not hold_transaction:
            raise ValueError(f"Транзакция удержания с ID '{operation_id}' не найдена.")

        if hold_transaction.transaction_type != 'HOLD':
            raise ValueError(f"Транзакция с ID '{operation_id}' не является операцией удержания.")
        
        if hold_transaction.transaction_status == 'CANCELLED':
            return {
                "operation_id": hold_transaction.transaction_id,
                "account_id": hold_transaction.account_id,
                "amount": float(hold_transaction.amount),
                "status": hold_transaction.transaction_status,
                "message": "Средства по данной операции уже отменены."
            }
        if hold_transaction.transaction_status == 'COMPLETED':
            raise ValueError(f"Транзакция с ID '{operation_id}' уже списана. Невозможно отменить удержание.")
        
        if hold_transaction.transaction_status != 'PENDING':
            raise ValueError(f"Транзакция с ID '{operation_id}' имеет статус '{hold_transaction.transaction_status}', невозможно отменить. Ожидается 'PENDING'.")

        account = db.query(Accounts).filter(
            Accounts.id == hold_transaction.account_id
        ).first()

        if not account:
            raise ValueError(f"Счет с ID '{hold_transaction.account_id}' для транзакции '{operation_id}' не найден.")

        amount_to_return = float(hold_transaction.amount)
       
        '''
        Успешная транзакция добавляется в таблицу
        '''

        hold_transaction.transaction_status = 'CANCELLED'
        hold_transaction.transaction_date = datetime.now(timezone.utc)

        account.held_balance = float(account.held_balance) - amount_to_return

        db.commit()

        return {
            "operation_id": hold_transaction.transaction_id,
            "account_id": account.account_number,
            "amount": amount_to_return,
            "status": hold_transaction.transaction_status,
            "message": "Удержание средств успешно отменено."
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def process_refund_funds(operation_id: str, description: str = "Возврат средств"):
    '''
    Реализация возврата средств на счет

    Входные аргументы:
    - `operation_id` - идентификатор операции, полученная из URL;
    - `description` - описание транзакции, по умолчанию установленная в "Возврат средств".

    Выходные данные - JSON-ответ:

    ```
    {
        "operation_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "refund_transaction_id": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY",
        "account_id": "ZZZZZZZZ-ZZZZ-ZZZZ-ZZZZ-ZZZZZZZZZZZZ",
        "amount": 100,
        "status": "COMPLETED",
        "message": "Средства успешно возвращены."
    }
    ```

    Ошибки:
    - `ValueError`:
        - счета не существует;
        - уже возвращено.
    '''

    db: Session = next(get_db())
    try:
        '''
        Поиск исходной транзакции списания (CHARGE) по operation_id
        Ищем оригинальную транзакцию (HOLD), которая была COMPLETED (списана)
        '''
        original_charge_transaction = db.query(Transactions).filter(
            Transactions.transaction_id == operation_id,
            Transactions.transaction_type == 'HOLD',
            Transactions.transaction_status == 'COMPLETED'
        ).first()

        if not original_charge_transaction:
            raise ValueError(f"Исходная транзакция списания (CHARGE) с ID '{operation_id}' не найдена или не имеет статус 'COMPLETED'.")

        '''
        Проверка, что по этой исходной транзакции ещё не было возврата
        Для этого используется поле original_transaction_id для проверки
        '''
        existing_refund_transaction = db.query(Transactions).filter(
            Transactions.original_transaction_id == original_charge_transaction.transaction_id,
            Transactions.transaction_type == 'REFUND'
        ).first()

        if existing_refund_transaction:
            return {
                "operation_id": original_charge_transaction.transaction_id,
                "refund_transaction_id": existing_refund_transaction.transaction_id,
                "account_id": existing_refund_transaction.account_id,
                "amount": float(existing_refund_transaction.amount),
                "status": existing_refund_transaction.transaction_status,
                "message": "Средства по данной операции уже были возвращены."
            }

        account = db.query(Accounts).filter(
            Accounts.id == original_charge_transaction.account_id
        ).first()

        if not account:
            raise ValueError(f"Счет с ID '{original_charge_transaction.account_id}' для исходной транзакции '{operation_id}' не найден.")

        amount_to_refund = float(original_charge_transaction.amount)

        '''
        Создание новой записи о транзакции возврата

        Во время выполнения транзакции генерируется UUID-транзакции возврата средств.
        
        Согласно таблице, также имеется ссылка на исходную транзакцию, откуда выполнялся возврат средств.
        '''
        refund_transaction_id = str(uuid.uuid4())
        new_refund_transaction = Transactions(
            transaction_id=refund_transaction_id,
            account_id=account.id,
            transaction_type='REFUND',
            transaction_date=datetime.now(timezone.utc),
            amount=amount_to_refund,
            description=f"{description} по операции {operation_id}",
            transaction_status='COMPLETED',
            original_transaction_id=original_charge_transaction.transaction_id
        )
        db.add(new_refund_transaction)

        '''
        Обновление баланса счета, то есть прибавка к текущему баланса значения, с которого ранее был сделан возврат.
        '''
        account.balance = float(account.balance) + amount_to_refund

        db.commit()
        db.refresh(new_refund_transaction)

        return {
            "operation_id": original_charge_transaction.transaction_id,
            "refund_transaction_id": new_refund_transaction.transaction_id,
            "account_id": account.account_number,
            "amount": float(new_refund_transaction.amount),
            "status": new_refund_transaction.transaction_status,
            "message": "Средства успешно возвращены."
        }

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
