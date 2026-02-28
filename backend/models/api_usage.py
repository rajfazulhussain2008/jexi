from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from database import Base


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=True)
    key_index = Column(Integer, default=0)  # which key in the rotation was used
    response_time = Column(Float, nullable=True)  # seconds
    tokens_used = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
