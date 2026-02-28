"""
health_service.py — Life Quantifier
Aggregates sleep, exercises, water, and mood logs to synthesize
a normalized 1..100 Life Score for DailyScore tracking.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from models.health_log import HealthLog
from models.journal import JournalEntry


class HealthService:
    @staticmethod
    def log(db: Session, user_id: int, data: dict) -> HealthLog | None:
        """Upsert a health log for an explicit (or today's) date."""
        try:
            d = data.get("date", datetime.now(timezone.utc).date())
            hlog = db.query(HealthLog).filter_by(user_id=user_id, date=d).first()
            if not hlog:
                hlog = HealthLog(user_id=user_id, date=d)
                db.add(hlog)

            if "sleep_hours" in data: hlog.sleep_hours = data["sleep_hours"]
            if "sleep_quality" in data: hlog.sleep_quality = data["sleep_quality"]
            if "water_liters" in data: hlog.water_liters = data["water_liters"]
            if "steps" in data: hlog.steps = data["steps"]
            if "exercise_type" in data: hlog.exercise_type = data["exercise_type"]
            if "exercise_duration" in data: hlog.exercise_duration = data["exercise_duration"]
            if "meals_logged" in data: hlog.meals_logged = data["meals_logged"]
            if "weight" in data: hlog.weight = data["weight"]
            if "notes" in data: hlog.notes = data["notes"]

            db.commit()
            db.refresh(hlog)
            return hlog
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_today(db: Session, user_id: int) -> HealthLog | None:
        try:
            today = datetime.now(timezone.utc).date()
            return db.query(HealthLog).filter_by(user_id=user_id, date=today).first()
        except:
            return None

    @staticmethod
    def get_trends(db: Session, user_id: int, metric: str, period: int = 30) -> list:
        try:
            start_date = datetime.now(timezone.utc).date() - timedelta(days=period)
            logs = db.query(HealthLog).filter(
                HealthLog.user_id == user_id, 
                HealthLog.date >= start_date
            ).order_by(HealthLog.date.asc()).all()
            
            return [{"date": str(l.date), "value": getattr(l, metric, None)} for l in logs if getattr(l, metric, None) is not None]
        except Exception:
            return []

    @staticmethod
    def calculate_score(db: Session, user_id: int, date=None) -> dict:
        """Calculate weighted score out of 100 based on standard health metrics."""
        try:
            d = date or datetime.now(timezone.utc).date()
            hlog = db.query(HealthLog).filter_by(user_id=user_id, date=d).first()
            if not hlog:
                return {"total": 0, "breakdown": {}}
            
            # Sub-scores
            sleep_score = min(30, ((hlog.sleep_hours or 0) / 8.0) * 30) # Out of 30, goal=8
            exercise_score = 25 if (hlog.exercise_duration and hlog.exercise_duration >= 20) else 0 # 25 for >20m
            water_score = min(20, ((hlog.water_liters or 0) / 2.5) * 20) # 2.5L goal
            meals_score = min(15, ((hlog.meals_logged or 0) / 3.0) * 15) # 3 meals
            quality_score = hlog.sleep_quality or 5 # 1-10 mapped to 10 points
            
            total = sleep_score + exercise_score + water_score + meals_score + quality_score
            
            return {
                "total": round(total, 1),
                "breakdown": {
                    "sleep": round(sleep_score, 1),
                    "exercise": exercise_score,
                    "water": round(water_score, 1),
                    "meals": round(meals_score, 1),
                    "quality": quality_score
                }
            }
        except Exception:
            return {"total": 0, "breakdown": {}}

    @staticmethod
    async def ai_insights(db: Session, user_id: int, llm_router) -> str:
        """Compare health correlations and generate health advice."""
        try:
            # Gather last 7 days of sleep/exercise and Journal Mood responses
            start_date = datetime.now(timezone.utc).date() - timedelta(days=7)
            hlogs = db.query(HealthLog).filter(HealthLog.user_id==user_id, HealthLog.date>=start_date).all()
            jlogs = db.query(JournalEntry).filter(JournalEntry.user_id==user_id, JournalEntry.date>=start_date).all()
            
            # We construct a textual prompt matching the records.
            data_arr = []
            for d in range(7):
                date_str = (start_date + timedelta(days=d)).isoformat()
                hl = next((h for h in hlogs if str(h.date) == date_str), None)
                jl = next((j for j in jlogs if str(j.date) == date_str), None)
                if hl or jl:
                    sleep = hl.sleep_hours if hl else "?"
                    ex = hl.exercise_duration if hl else "?"
                    mood = jl.mood_score if jl else "?"
                    data_arr.append(f"Day {d}: Sleep={sleep}h, Exercise={ex}m, Mood={mood}/10")
            
            prompt = (
                "Based on my recent health and mood logs, write 2 concise, supportive pieces of health advice "
                "or point out a trend:\n" + "\n".join(data_arr)
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=86400)
            return resp.get("text", "Get consistent sleep and stay hydrated.")
        except Exception:
            return "Unable to fetch health insights right now."
