from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint
from database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    content = Column(Text, nullable=True)
    mood_score = Column(Integer, nullable=True)  # 1-10
    energy_score = Column(Integer, nullable=True)  # 1-10
    tags = Column(Text, nullable=True)  # JSON array
    gratitude = Column(Text, nullable=True)  # JSON array of strings
    wins = Column(Text, nullable=True)  # JSON array of strings
    challenges = Column(Text, nullable=True)  # JSON array of strings
    tomorrow_intention = Column(Text, nullable=True)
    ai_analysis = Column(Text, nullable=True)  # JSON — sentiment, emotions, themes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_journal_user_date"),
    )
