import uuid
from sqlalchemy import Column, DECIMAL, DateTime, UUID
from sqlalchemy.sql import func
from .base import Base


class AccountBalance(Base):
    __tablename__ = 'account_balances'
    account_id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    authorized_balance = Column(DECIMAL(10, 2), default=0.00, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<AccountBalance {self.account_id} | Authorized: {self.authorized_balance}>"