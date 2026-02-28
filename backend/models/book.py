from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    author = Column(String(200), nullable=True)
    total_pages = Column(Integer, default=1)
    current_page = Column(Integer, default=0)
    status = Column(String(20), default="reading")  # to_read/reading/completed/dropped
    notes = Column(Text, nullable=True)  # JSON array of reading notes
    rating = Column(Integer, nullable=True)  # 1-5
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
