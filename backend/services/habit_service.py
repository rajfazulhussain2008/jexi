"""
habit_service.py — Habits & Streaks tracking
Logs daily habits, calculates streaks iteratively (backward-looking), and queries stats.
"""

import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.habit import Habit
from models.habit_log import HabitLog


class HabitService:
    @staticmethod
    def create(db: Session, user_id: int, data: dict) -> Habit | None:
        try:
            h = Habit(
                user_id=user_id,
                name=data.get("name"),
                icon=data.get("icon", "✅"),
                frequency=data.get("frequency", "daily"),
                custom_days=json.dumps(data.get("custom_days", [])),
                target=data.get("target"),
                reminder_time=data.get("reminder_time"),
                category=data.get("category"),
                difficulty=data.get("difficulty", "medium")
            )
            db.add(h)
            db.commit()
            db.refresh(h)
            return h
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_all(db: Session, user_id: int) -> list[dict]:
        """All habits with today's status."""
        try:
            habits = db.query(Habit).filter_by(user_id=user_id).all()
            today = datetime.now(timezone.utc).date()
            result = []
            for h in habits:
                log = db.query(HabitLog).filter_by(habit_id=h.id, date=today).first()
                result.append({
                    "habit": h,
                    "completed_today": log.completed if log else False
                })
            return result
        except Exception:
            return []

    @staticmethod
    def update(db: Session, user_id: int, habit_id: int, data: dict) -> Habit | None:
        try:
            h = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
            if not h: return None
            for k, v in data.items():
                if hasattr(h, k):
                    if k == "custom_days" and isinstance(v, list):
                        setattr(h, k, json.dumps(v))
                    else:
                        setattr(h, k, v)
            db.commit()
            db.refresh(h)
            return h
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def delete(db: Session, user_id: int, habit_id: int) -> bool:
        try:
            h = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
            if h:
                db.delete(h)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def check(db: Session, user_id: int, habit_id: int, date=None, value=None) -> dict:
        """Mark completed, calc streak, trigger milestones."""
        try:
            d = date or datetime.now(timezone.utc).date()
            h = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
            if not h: return {}

            log = db.query(HabitLog).filter_by(habit_id=habit_id, date=d).first()
            if log:
                log.completed = True
                log.value = value
            else:
                log = HabitLog(habit_id=habit_id, date=d, completed=True, value=value)
                db.add(log)
            db.commit()

            streak = HabitService.calculate_streak(db, habit_id)
            milestones = [7, 14, 21, 30, 60, 90, 100, 365]
            reached = streak in milestones

            return {
                "streak": streak,
                "milestone_reached": reached,
                "milestone_type": f"{streak} days" if reached else None
            }
        except Exception:
            db.rollback()
            return {}

    @staticmethod
    def uncheck(db: Session, user_id: int, habit_id: int, date=None):
        try:
            d = date or datetime.now(timezone.utc).date()
            log = db.query(HabitLog).filter(
                HabitLog.habit_id == habit_id,
                HabitLog.habit.has(user_id=user_id),
                HabitLog.date == d
            ).first()
            if log:
                log.completed = False
                db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def calculate_streak(db: Session, habit_id: int) -> int:
        """Count backward consecutive. 1 day grace period for today."""
        try:
            logs = db.query(HabitLog).filter_by(habit_id=habit_id, completed=True)\
                     .order_by(HabitLog.date.desc()).all()
                     
            if not logs: return 0

            today = datetime.now(timezone.utc).date()
            streak = 0
            curr_date = today

            # 1-day grace: user doesn't lose streak if they haven't done it TODAY yet
            # So start checking from yesterday if today's log doesn't exist
            if logs[0].date != today:
                curr_date = today - timedelta(days=1)

            for log in logs:
                if log.date == curr_date:
                    streak += 1
                    curr_date -= timedelta(days=1)
                elif log.date > curr_date:
                    continue  # Should be impossible due to order_by
                else: 
                    # Missing day
                    break
            
            return streak
        except Exception:
            return 0

    @staticmethod
    def get_history(db: Session, user_id: int, habit_id: int, period="month") -> list:
        try:
            start_date = datetime.now(timezone.utc).date() - timedelta(days=30)
            logs = db.query(HabitLog).filter(
                HabitLog.habit_id == habit_id,
                HabitLog.date >= start_date
            ).all()
            return [{"date": str(l.date), "completed": l.completed} for l in logs]
        except Exception:
            return []

    @staticmethod
    def get_today(db: Session, user_id: int) -> list:
        return HabitService.get_all(db, user_id)

    @staticmethod
    def get_streaks(db: Session, user_id: int) -> list:
        try:
            habits = db.query(Habit).filter_by(user_id=user_id).all()
            return [{"habit": h.name, "streak": HabitService.calculate_streak(db, h.id)} for h in habits]
        except Exception:
            return []

    @staticmethod
    def get_stats(db: Session, user_id: int, period="month") -> dict:
        """Placeholder for aggregate completion rate over month."""
        return {"completion_rate": 0.0}

    @staticmethod
    async def ai_insights(db: Session, user_id: int, llm_router) -> str:
        try:
            streaks = HabitService.get_streaks(db, user_id)
            data_str = ", ".join([f"{s['habit']}: {s['streak']} days" for s in streaks])
            prompt = "Analyze these habit streaks and give me 2 short sentences of actionable insights: " + data_str
            resp = await llm_router.route([{"role": "user", "content": prompt}])
            return resp.get("text", "Keep up the good work!")
        except Exception:
            return ""
