from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user/assistant/system
    content = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    response_time = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
