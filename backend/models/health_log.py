from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey, UniqueConstraint
from database import Base


class HealthLog(Base):
    __tablename__ = "health_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    sleep_hours = Column(Float, nullable=True)
    sleep_quality = Column(Integer, nullable=True)  # 1-10
    water_liters = Column(Float, nullable=True)
    steps = Column(Integer, nullable=True)
    exercise_type = Column(String(100), nullable=True)
    exercise_duration = Column(Integer, nullable=True)  # minutes
    meals_logged = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_healthlog_user_date"),
    )
