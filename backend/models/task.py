from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")  # urgent/high/medium/low
    status = Column(String(20), default="pending")  # pending/in_progress/done/archived
    due_date = Column(DateTime, nullable=True)
    category = Column(String(50), nullable=True)  # work/personal/learning/health/other
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    estimated_time = Column(Integer, nullable=True)  # minutes
    tags = Column(Text, nullable=True)  # JSON array string
    subtasks = Column(Text, nullable=True)  # JSON array of {title, done} objects
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
