from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP
from core.models.base import Base

class Clients(Base):
    first_name: Mapped[str] = mapped_column(nullable = False)
    last_name: Mapped[str] = mapped_column(nullable = False)
    middle_name: Mapped[str] = mapped_column(nullable = True)
    date_of_birth: Mapped[str] 
    address: Mapped[str]
    phone_number: Mapped[str]
    registration_date: Mapped[str] = mapped_column(TIMESTAMP)