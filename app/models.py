import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DECIMAL, DateTime, Boolean, UUID, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Transaction(Base):
    """
    Типы значений и ограничения сопоставлены с таковыми из app/schemas.py
    """
    __tablename__ = 'transactions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    invoice_id = Column(String(15), nullable=False, index=True)
    invoice_id_alt = Column(String(15), nullable=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    name = Column(String(255), nullable=False)
    hpan = Column(String(16), nullable=False)
    exp_date = Column(String(4), nullable=False)
    cvc = Column(String(3), nullable=True)
    status = Column(String(50), nullable=False, default='NEW')
    description = Column(String(1024), nullable=False)
    account_id = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(15), nullable=True)
    post_link = Column(String(2048), nullable=False)
    failure_post_link = Column(String(2048), nullable=True)
    card_save = Column(Boolean, nullable=False)
    data = Column(String(4096), nullable=True)
    terminal_id = Column(String(255), nullable=True)
    reference = Column(String(255), nullable=True)
    int_reference = Column(String(255), nullable=True)
    approval_code = Column(String(6), nullable=True)
    card_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Transaction(id='{self.id}', invoice_id='{self.invoice_id}', amount={self.amount}, status='{self.status}')>"