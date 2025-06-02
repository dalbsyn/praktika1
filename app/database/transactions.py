from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import TIMESTAMP, VARCHAR, UUID, DECIMAL, ForeignKey, TEXT
from app.database.base import Base
import datetime

class Transactions(Base):
    transaction_id: Mapped[str] = mapped_column(UUID, unique=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id', ondelete='restrict'), nullable=False)
    transaction_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    transaction_date: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=False)
    description: Mapped[str] = mapped_column(TEXT)
    transaction_status: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    original_transaction_id: Mapped[str] = mapped_column(UUID, nullable=True, default=None)