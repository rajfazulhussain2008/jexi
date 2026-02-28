from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base


class LearningCourse(Base):
    __tablename__ = "learning_courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    platform = Column(String(100), nullable=True)  # Udemy/YouTube/Coursera/etc
    url = Column(String(500), nullable=True)
    total_lessons = Column(Integer, default=1)
    completed_lessons = Column(Integer, default=0)
    status = Column(String(20), default="in_progress")  # not_started/in_progress/completed/dropped
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
