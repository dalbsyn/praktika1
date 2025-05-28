from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import TIMESTAMP, DATE, TEXT, VARCHAR
from core.models.base import Base


class Clients(Base):
    first_name: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    last_name: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    middle_name: Mapped[str] = mapped_column(VARCHAR(64), nullable=True)
    date_of_birth: Mapped[str] = mapped_column(DATE)
    address: Mapped[str] = mapped_column(TEXT)
    phone_number: Mapped[str] = mapped_column(VARCHAR(20))
    registration_date: Mapped[str] = mapped_column(TIMESTAMP)
