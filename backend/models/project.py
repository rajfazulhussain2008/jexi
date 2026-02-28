from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    tech_stack = Column(Text, nullable=True)  # JSON array
    status = Column(String(20), default="planning")  # planning/active/paused/completed/abandoned
    deadline = Column(DateTime, nullable=True)
    github_url = Column(String(500), nullable=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    total_time_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
