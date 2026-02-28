"""
journal_service.py — AI-Automated Journaling
Supports journal creation, daily auto prompt gen, mood aggregations, and 
period-based analytical NLP summaries of entries via LLMs.
"""

import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import extract

from models.journal import JournalEntry


class JournalService:
    @staticmethod
    async def create(db: Session, user_id: int, data: dict, llm_router=None) -> JournalEntry | None:
        try:
            d = data.get("date", datetime.now(timezone.utc).date())
            entry = db.query(JournalEntry).filter_by(user_id=user_id, date=d).first()
            if not entry:
                entry = JournalEntry(user_id=user_id, date=d)
            
            entry.content = data.get("content", entry.content)
            entry.mood_score = data.get("mood_score", entry.mood_score)
            entry.energy_score = data.get("energy_score", entry.energy_score)
            
            if "tags" in data: entry.tags = json.dumps(data["tags"])
            if "gratitude" in data: entry.gratitude = json.dumps(data["gratitude"])
            if "wins" in data: entry.wins = json.dumps(data["wins"])
            if "challenges" in data: entry.challenges = json.dumps(data["challenges"])
            if "tomorrow_intention" in data: entry.tomorrow_intention = data["tomorrow_intention"]
            
            if llm_router and entry.content:
                # Run Auto-analysis
                prompt = (
                    "Analyze this journal entry. Return ONLY a JSON object: "
                    '{"sentiment": "positive/negative/neutral", "emotions": ["..."], "themes": ["..."]}. Text: '
                    + entry.content
                )
                resp = await llm_router.route([{"role": "user", "content": prompt}])
                text_resp = resp.get("text", "")
                
                # Excerpt and validate JSON
                try:
                    start = text_resp.find("{")
                    end = text_resp.rfind("}") + 1
                    valid_json = text_resp[start:end]
                    json.loads(valid_json) # Test it
                    entry.ai_analysis = valid_json
                except:
                    pass

            entry.updated_at = datetime.now(timezone.utc)
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_all(db: Session, user_id: int, filters: dict = None) -> list[JournalEntry]:
        try:
            return db.query(JournalEntry).filter_by(user_id=user_id).order_by(JournalEntry.date.desc()).all()
        except:
            return []

    @staticmethod
    def get_by_date(db: Session, user_id: int, date) -> JournalEntry | None:
        try:
            return db.query(JournalEntry).filter_by(user_id=user_id, date=date).first()
        except:
            return None

    @staticmethod
    async def get_prompts(db: Session, user_id: int, llm_router) -> list[str]:
        """Generate AI personalized journal prompts."""
        try:
            prompt = (
                "Give me exactly 3 interesting and self-reflective personalized journal prompts for today. "
                "Base them on general themes of growth and focus. "
                "Return ONLY a valid JSON array of strings: ['prompt 1', 'prompt 2', 'prompt 3']."
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=3600)
            text_resp = resp.get("text", "")
            try:
                start = text_resp.find("[")
                end = text_resp.rfind("]") + 1
                return json.loads(text_resp[start:end])
            except:
                return ["What challenged you today?", "What are you grateful for?"]
        except Exception:
            return ["What challenged you today?", "What are you grateful for?"]

    @staticmethod
    def get_mood_trends(db: Session, user_id: int, period="month") -> list:
        """Extract mood/energy fields for line charting."""
        try:
            start_date = datetime.now(timezone.utc).date() - timedelta(days=30)
            entries = db.query(JournalEntry).filter(
                JournalEntry.user_id == user_id, 
                JournalEntry.date >= start_date
            ).all()
            return [{"date": str(e.date), "mood_score": e.mood_score, "energy_score": e.energy_score} for e in entries]
        except Exception:
            return []

    @staticmethod
    def get_correlations(db: Session, user_id: int) -> dict:
        """Placeholder for cross-table aggregations via memory/health."""
        return {}

    @staticmethod
    async def ai_summary(db: Session, user_id: int, period: str, llm_router) -> str:
        """Analyze journaling text for the period and construct a narrative reflection."""
        try:
            days = 7 if period == "week" else 30
            start_date = datetime.now(timezone.utc).date() - timedelta(days=days)
            entries = db.query(JournalEntry).filter(
                JournalEntry.user_id == user_id, 
                JournalEntry.date >= start_date,
                JournalEntry.content != None
            ).all()
            
            if not entries: return "Not enough journal data to summarize."
            
            combined = "\n\n".join([f"Date: {e.date}\nContent: {e.content}" for e in entries])
            prompt = (
                f"Act as a therapist summarizing my journals over the last {period}. "
                "Identify themes, patterns, emotional arc, and insights. "
                "Here are the entries:\n" + combined
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=86400)
            return resp.get("text", "Error generating summary.")
        except Exception:
            return "Failed to generate AI summary."

    @staticmethod
    def on_this_day(db: Session, user_id: int) -> list:
        try:
            today = datetime.now(timezone.utc).date()
            # MySQL/SQLite/Postgres friendly generic filtering
            entries = db.query(JournalEntry).filter(
                JournalEntry.user_id == user_id,
                extract('month', JournalEntry.date) == today.month,
                extract('day', JournalEntry.date) == today.day,
                extract('year', JournalEntry.date) != today.year
            ).all()
            return entries
        except:
            return []
