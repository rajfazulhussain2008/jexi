from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from database import Base


class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(200), nullable=False)
    value = Column(Text, nullable=False)
    auto_extracted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_memory_user_key"),
    )
