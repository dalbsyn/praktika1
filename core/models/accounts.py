from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import TIMESTAMP, VARCHAR, UUID, DECIMAL, ForeignKey
from core.models.base import Base


class Accounts(Base):
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="cascade"))
    account_number: Mapped[str] = mapped_column(UUID, nullable=False, unique=True)
    account_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=False, default=0.00)
    currency: Mapped[str] = mapped_column(VARCHAR(3), nullable=False)
    openning_date: Mapped[str] = mapped_column(TIMESTAMP)
