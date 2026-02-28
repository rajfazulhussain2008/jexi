from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from database import Base


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    period = Column(String(20), default="monthly")  # weekly/monthly

    __table_args__ = (
        UniqueConstraint("user_id", "category", "period", name="uq_budget_user_category_period"),
    )
