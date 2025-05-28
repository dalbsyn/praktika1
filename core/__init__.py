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

from core.models.base import Base
from core.models.clients import Clients
from core.models.accounts import Accounts
from core.models.cards import Cards
from core.models.transactions import Transactions