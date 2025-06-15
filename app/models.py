import uuid
from datetime import datetime, timezone
from sqlalchemy.sql import func
from sqlalchemy import Column, String, DECIMAL, DateTime, Boolean, UUID, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Transaction(Base):
    """
    Типы значений и ограничения сопоставлены с таковыми из app/schemas.py
    """
    __tablename__ = 'transactions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    invoice_id = Column(String(15), nullable=False, index=True, unique=True)
    invoice_id_alt = Column(String(15), nullable=True, unique=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    name = Column(String(255), nullable=False)
    hpan = Column(String(16), nullable=False)
    exp_date = Column(String(4), nullable=False)
    cvc = Column(String(3), nullable=True)
    status = Column(String(50), nullable=False, default='NEW')
    description = Column(Text(), nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=True,
                        default=lambda: uuid.uuid4())
    email = Column(String(255), nullable=True)
    phone = Column(String(15), nullable=True)
    post_link = Column(String(2048), nullable=False)
    failure_post_link = Column(String(2048), nullable=True)
    card_save = Column(Boolean, nullable=False)
    data = Column(Text(), nullable=True)
    terminal_id = Column(UUID(as_uuid=True), nullable=True, default=lambda: uuid.uuid4())
    reference = Column(String(255), nullable=True)
    int_reference = Column(String(255), nullable=True)
    approval_code = Column(String(6), nullable=True)
    card_id = Column(UUID(as_uuid=True), nullable=True, default=lambda: uuid.uuid4())
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Transaction(id='{self.id}', invoice_id='{self.invoice_id}', amount={self.amount}, status='{self.status}')>"


class AccountBalance(Base):
    __tablename__ = 'account_balances'
    account_id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    authorized_balance = Column(DECIMAL(10, 2), default=0.00, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<AccountBalance {self.account_id} | Authorized: {self.authorized_balance}>"


