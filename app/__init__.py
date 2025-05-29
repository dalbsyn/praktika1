'''
Здесь происходит импорт всех таблиц, включая базовый шаблон для них, 
от которого в дальнейшем происходят все миграции. 

Сперва важно импортировать сами таблицы, потом нужно добавить его в список
__all__
'''

__all__ = (
    'Base',
    'Clients',
    'Accounts',
    'Cards',
    'Transactions'
)

from app.database.base import Base
from app.database.clients import Clients
from app.database.accounts import Accounts
from app.database.cards import Cards
from app.database.transactions import Transactions