from sqlalchemy import Column, Integer, String, Float, Text, Date, ForeignKey, UniqueConstraint
from database import Base


class DailyScore(Base):
    __tablename__ = "daily_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    tasks_score = Column(Float, default=0)  # out of 20
    habits_score = Column(Float, default=0)  # out of 20
    health_score = Column(Float, default=0)  # out of 20
    goals_score = Column(Float, default=0)  # out of 20
    coding_score = Column(Float, default=0)  # out of 20
    total_score = Column(Float, default=0)  # out of 100
    breakdown = Column(Text, nullable=True)  # JSON — detailed breakdown

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_dailyscore_user_date"),
    )
