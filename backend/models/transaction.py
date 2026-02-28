from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, Boolean, ForeignKey
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(20), nullable=False)  # income/expense
    category = Column(String(50), nullable=False)  # food/rent/transport/shopping/entertainment/learning/salary/freelance/other
    description = Column(String(500), nullable=True)
    date = Column(Date, nullable=False)
    payment_method = Column(String(20), nullable=True)  # cash/card/upi/bank
    is_recurring = Column(Boolean, default=False)
    recurring_frequency = Column(String(20), nullable=True)  # daily/weekly/monthly/yearly
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
