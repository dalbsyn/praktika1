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

from core.database.base import Base
from core.database.clients import Clients
from core.database.accounts import Accounts
from core.database.cards import Cards
from core.database.transactions import Transactions