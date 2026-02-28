from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from database import Base


class DevSession(Base):
    __tablename__ = "dev_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    pause_duration = Column(Integer, default=0)  # minutes
    total_minutes = Column(Integer, nullable=True)
    mode = Column(String(20), nullable=True)  # teacher/pair/reviewer/debug/speed/challenge
    tasks_completed = Column(Text, nullable=True)  # JSON array
    concepts_learned = Column(Text, nullable=True)  # JSON array
    focus_score = Column(Integer, nullable=True)  # 1-10
    is_active = Column(Boolean, default=True)
