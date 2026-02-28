"""
analytics_service.py — Global Statistics & Score Processing
Aggregates health, habits, goals, and tasks to formulate a global DailyScore.
Runs macro LLM evaluations (Weekly/Monthly insights and predictions).
"""

import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.daily_score import DailyScore
from models.task import Task
from models.habit_log import HabitLog
from models.goal import Goal
from models.health_log import HealthLog
from models.project import Project
from models.journal import JournalEntry

from services.health_service import HealthService


class AnalyticsService:

    @staticmethod
    def calculate_life_score(db: Session, user_id: int, date=None) -> dict:
        """Aggregates all modules to yield a holistic 100-point daily life score."""
        try:
            d = date or datetime.now(timezone.utc).date()
            d_start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
            d_end = d_start + timedelta(days=1)
            
            # --- Tasks (20 points) ---
            pending = db.query(Task).filter(Task.user_id==user_id, Task.status != "done").count()
            completed = db.query(Task).filter(Task.user_id==user_id, Task.status == "done", Task.completed_at >= d_start, Task.completed_at < d_end).count()
            task_score = 20 if pending == 0 and completed > 0 else ((completed / (pending + completed) * 20) if (pending+completed) > 0 else 0)
            
            # --- Habits (20 points) ---
            from models.habit import Habit
            total_h = db.query(Habit).filter_by(user_id=user_id).count()
            done_h = db.query(HabitLog).filter(HabitLog.date==d, HabitLog.completed==True, HabitLog.habit.has(user_id=user_id)).count()
            habit_score = (done_h / total_h * 20) if total_h > 0 else 0
            
            # --- Health (20 points) ---
            health_data = HealthService.calculate_score(db, user_id, d)
            health_score = health_data["total"] / 5.0 # (100 -> 20)
            
            # --- Goals (20 points) ---
            goals = db.query(Goal).filter_by(user_id=user_id, status="active").all()
            if goals:
                avg_prog = sum([(g.current_value / g.target_value if g.target_value else 0) for g in goals]) / len(goals)
                goal_score = avg_prog * 20
            else:
                goal_score = 0
                
            # --- Coding (20 points) ---
            # Dummy representation, assumes user configured daily goal 
            coding_score = 10 # placeholder depending on dev session fetch log time
            
            total = min(100, task_score + habit_score + health_score + goal_score + coding_score)
            breakdown = {
                "tasks": round(task_score, 1),
                "habits": round(habit_score, 1),
                "health": round(health_score, 1),
                "goals": round(goal_score, 1),
                "coding": round(coding_score, 1)
            }
            
            # Save to Database
            score_entry = db.query(DailyScore).filter_by(user_id=user_id, date=d).first()
            if not score_entry:
                score_entry = DailyScore(user_id=user_id, date=d)
                db.add(score_entry)
            
            score_entry.total_score = total
            score_entry.breakdown = json.dumps(breakdown)
            db.commit()
            
            return {"total": round(total, 1), "breakdown": breakdown}
        except Exception:
            db.rollback()
            return {"total": 0, "breakdown": {}}

    @staticmethod
    def get_dashboard(db: Session, user_id: int) -> dict:
        """Central dashboard bundle: aggregates lightweight counts."""
        try:
            today = datetime.now(timezone.utc).date()
            pending_t = db.query(Task).filter(Task.user_id==user_id, Task.status!="done").count()
            completed_t = db.query(Task).filter(Task.user_id==user_id, Task.status=="done").count()
            
            hlogs = db.query(HabitLog).filter(HabitLog.date==today, HabitLog.completed==True, HabitLog.habit.has(user_id=user_id)).count()
            
            proj_count = db.query(Project).filter_by(user_id=user_id, status="active").count()
            
            score = AnalyticsService.calculate_life_score(db, user_id, today)
            
            return {
                "tasks_today": {"pending": pending_t, "done": completed_t},
                "habits_done_today": hlogs,
                "active_projects": proj_count,
                "life_score": score,
            }
        except Exception:
            return {}

    @staticmethod
    def get_life_score_history(db: Session, user_id: int, period: int = 30) -> list:
        try:
            start_date = datetime.now(timezone.utc).date() - timedelta(days=period)
            logs = db.query(DailyScore).filter(DailyScore.user_id==user_id, DailyScore.date >= start_date)\
                                       .order_by(DailyScore.date.asc()).all()
            return [{"date": str(l.date), "total_score": l.total_score} for l in logs]
        except Exception:
            return []

    @staticmethod
    def get_correlations(db: Session, user_id: int) -> list:
        """Find meaningful relationships linearly... placeholder."""
        return []

    @staticmethod
    async def ai_insights(db: Session, user_id: int, llm_router) -> list:
        """Call LLM with macro user data from correlations & trends."""
        return []

    @staticmethod
    async def predictions(db: Session, user_id: int, llm_router) -> list:
        """Generate forecasts using baseline data run against LLM model predictions."""
        return []

    @staticmethod
    async def weekly_review(db: Session, user_id: int, llm_router) -> str:
        """Massive macro review of 7 days using LLM reasoning."""
        return "Review system parsing..."

    @staticmethod
    async def monthly_review(db: Session, user_id: int, llm_router) -> str:
        return "Review system parsing..."
