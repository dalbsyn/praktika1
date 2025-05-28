from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    '''
    Базовый класс для других таблиц в базе данных.
    Таблицы автоматом называются именем Python-класса в нижнем регистре, а
    также создается столбец идентификатора в каждой таблице как первичный ключ. 
    '''
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    id: Mapped[int] = mapped_column(primary_key=True)
