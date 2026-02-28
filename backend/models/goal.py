from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    goal_type = Column(String(20), nullable=False)  # life/yearly/quarterly/monthly/weekly
    target_value = Column(Float, nullable=True)  # e.g., 5.0 for "5 projects"
    current_value = Column(Float, default=0.0)
    deadline = Column(DateTime, nullable=True)
    parent_goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    category = Column(String(50), nullable=True)  # career/health/finance/learning/personal
    milestones = Column(Text, nullable=True)  # JSON array of {title, target, reached} objects
    status = Column(String(20), default="active")  # active/completed/paused/abandoned
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
