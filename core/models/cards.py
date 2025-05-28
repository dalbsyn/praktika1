from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import TIMESTAMP, VARCHAR, UUID, DECIMAL, ForeignKey, DATE
from core.models.base import Base


class Cards(Base):
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id', ondelete='cascade'))
    card_number: Mapped[str] = mapped_column(VARCHAR(20), unique=True, nullable=False)
    expiry_date: Mapped[str] = mapped_column(DATE, nullable=False)
    cvc: Mapped[str] = mapped_column(VARCHAR(4), nullable=False)
    cardholder_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    issue_date: Mapped[str] = mapped_column(TIMESTAMP)
    card_status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default='active')