"""
finance_service.py — Finance & Budgets
Extracts transaction details from natural text, compiles summaries,
computes budget health, and delivers AI-driven money advice.
"""

import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from models.transaction import Transaction
from models.budget import Budget
from models.user import User


class FinanceService:
    @staticmethod
    def create_transaction(db: Session, user_id: int, data: dict) -> Transaction | None:
        try:
            t = Transaction(
                user_id=user_id,
                amount=data.get("amount", 0.0),
                type=data.get("type", "expense"),
                category=data.get("category", "other"),
                description=data.get("description", ""),
                date=data.get("date", datetime.now(timezone.utc).date()),
                payment_method=data.get("payment_method"),
                is_recurring=data.get("is_recurring", False),
                recurring_frequency=data.get("recurring_frequency")
            )
            db.add(t)
            db.commit()
            db.refresh(t)
            return t
        except Exception:
            db.rollback()
            return None

    @staticmethod
    async def ai_parse_transaction(text: str, llm_router) -> dict | None:
        """Parse natural language into a Transaction object via LLM."""
        try:
            prompt = (
                "Parse this into a financial transaction. Return ONLY valid JSON: "
                '{"amount": 10.5, "type": "income/expense", "category": "food/rent/transport/shopping/entertainment/learning/salary/freelance/other", '
                '"description": "coffee", "date": "YYYY-MM-DD"}. Text: '
                + text
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=0)
            text_resp = resp.get("text", "")
            start = text_resp.find("{")
            end = text_resp.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            return json.loads(text_resp[start:end])
        except Exception:
            return None

    @staticmethod
    def get_transactions(db: Session, user_id: int, filters: dict = None) -> list:
        try:
            query = db.query(Transaction).filter_by(user_id=user_id)
            if filters:
                if "type" in filters:
                    query = query.filter_by(type=filters["type"])
                if "category" in filters:
                    query = query.filter_by(category=filters["category"])
                # Could add date range filters
            return query.order_by(Transaction.date.desc()).all()
        except:
            return []

    @staticmethod
    def get_summary(db: Session, user_id: int, period: str = "month") -> dict:
        """Total income, expenses, and savings rate."""
        try:
            today = datetime.now(timezone.utc).date()
            if period == "month":
                start_date = today.replace(day=1)
            else:
                start_date = today - timedelta(days=7)

            txs = db.query(Transaction).filter(
                Transaction.user_id == user_id, 
                Transaction.date >= start_date
            ).all()

            income = sum(t.amount for t in txs if t.type == "income")
            expenses = sum(t.amount for t in txs if t.type == "expense")
            
            # Category breakdown (expenses only)
            cats = {}
            for t in txs:
                if t.type == "expense":
                    cats[t.category] = cats.get(t.category, 0) + t.amount
                    
            breakdown = [{"category": k, "amount": v, "percentage": (v/expenses)*100 if expenses else 0} 
                       for k, v in cats.items()]

            return {
                "total_income": income,
                "total_expenses": expenses,
                "net_savings": income - expenses,
                "savings_rate": ((income - expenses) / income) * 100 if income > 0 else 0,
                "category_breakdown": sorted(breakdown, key=lambda x: x["amount"], reverse=True)
            }
        except Exception:
            return {}

    @staticmethod
    def create_budget(db: Session, user_id: int, data: dict) -> Budget | None:
        try:
            b = Budget(
                user_id=user_id,
                category=data.get("category"),
                amount=data.get("amount"),
                period=data.get("period", "monthly")
            )
            db.add(b)
            db.commit()
            db.refresh(b)
            return b
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_budget_status(db: Session, user_id: int) -> list:
        try:
            today = datetime.now(timezone.utc).date()
            start_date = today.replace(day=1) # monthly

            budgets = db.query(Budget).filter_by(user_id=user_id, period="monthly").all()
            status = []
            
            for b in budgets:
                spent = db.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user_id,
                    Transaction.category == b.category,
                    Transaction.type == "expense",
                    Transaction.date >= start_date
                ).scalar() or 0.0
                
                status.append({
                    "category": b.category,
                    "budget_amount": b.amount,
                    "spent_amount": spent,
                    "remaining": b.amount - spent,
                    "percentage_used": (spent / b.amount) * 100 if b.amount else 0
                })
            return status
        except Exception:
            return []

    @staticmethod
    def get_savings_goal(db: Session, user_id: int) -> dict:
        try:
            user = db.query(User).filter_by(id=user_id).first()
            if not user or not user.settings: return {}
            
            settings = json.loads(user.settings)
            target = settings.get("target_savings", 0)
            
            if not target: return {}

            # Estimate based on avg monthly savings over last 6 months
            # (Simplified version here)
            summary = FinanceService.get_summary(db, user_id, "month")
            monthly_rate = summary.get("net_savings", 0)
            
            current_total = 0 # would be aggregated lifetime but placeholder
            
            days_left = ((target - current_total) / monthly_rate) * 30 if monthly_rate > 0 else 0
            
            return {
                "target": target,
                "current": current_total,
                "monthly_rate": monthly_rate,
                "estimated_completion_date": str(datetime.now(timezone.utc).date() + timedelta(days=days_left)) if days_left > 0 else None
            }
        except Exception:
            return {}

    @staticmethod
    async def ai_insights(db: Session, user_id: int, llm_router) -> str:
        try:
            summary = FinanceService.get_summary(db, user_id, "month")
            prompt = (
                "Based on this monthly finance summary, give me 3 concise lines of personalized money advice "
                "or actionable insights: " + json.dumps(summary)
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}])
            return resp.get("text", "Track your spending carefully.")
        except Exception:
            return "Unable to fetch insights right now."

    @staticmethod
    def get_trends(db: Session, user_id: int) -> list:
        """Return monthly totals for last 12 months for UI charts."""
        try:
            # Query grouped by month (SQLite logic compatible via string matching)
            # Placeholder implementation returning empty mapping formatting.
            return []
        except Exception:
            return []
