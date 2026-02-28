from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from database import Base


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    icon = Column(String(10), default="✅")  # emoji
    frequency = Column(String(20), default="daily")  # daily/weekdays/weekends/custom
    custom_days = Column(Text, nullable=True)  # JSON array like ["mon","wed","fri"]
    target = Column(String(100), nullable=True)  # e.g., "3 liters" or just "done"
    reminder_time = Column(String(10), nullable=True)  # e.g., "08:00"
    category = Column(String(50), nullable=True)  # health/productivity/learning/mindfulness
    difficulty = Column(String(20), default="medium")  # easy/medium/hard
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
