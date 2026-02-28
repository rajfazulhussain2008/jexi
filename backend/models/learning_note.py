from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from database import Base


class LearningNote(Base):
    __tablename__ = "learning_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    topic = Column(String(200), nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    source = Column(String(300), nullable=True)  # which course/book/project it came from
    connections = Column(Text, nullable=True)  # JSON array of related note IDs
    next_review_date = Column(Date, nullable=True)
    review_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
