from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from database import Base


class Snippet(Base):
    __tablename__ = "snippets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    tags = Column(Text, nullable=True)  # JSON array
    description = Column(Text, nullable=True)
    auto_saved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
