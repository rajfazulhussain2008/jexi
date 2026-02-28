from sqlalchemy import Column, Integer, String, Text, Date, Boolean, ForeignKey, UniqueConstraint
from database import Base


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False)
    date = Column(Date, nullable=False)
    completed = Column(Boolean, default=False)
    value = Column(String(100), nullable=True)  # e.g., "2.5 liters"
    note = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="uq_habit_date"),
    )
