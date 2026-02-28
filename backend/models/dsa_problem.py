from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from database import Base


class DSAProblem(Base):
    __tablename__ = "dsa_problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy/medium/hard
    topic = Column(String(100), nullable=False)  # arrays/strings/hash_maps/linked_lists/trees/graphs/dp/sorting/recursion/stacks_queues
    description = Column(Text, nullable=False)
    examples = Column(Text, nullable=True)  # JSON array of {input, output, explanation}
    hints = Column(Text, nullable=True)  # JSON array of 3 hints
    solution = Column(Text, nullable=True)
    user_solution = Column(Text, nullable=True)
    solved = Column(Boolean, default=False)
    time_taken = Column(Integer, nullable=True)  # minutes
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
