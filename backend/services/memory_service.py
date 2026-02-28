"""
memory_service.py — AI Memory & Context Builder
Manages Conversation history, MemoryFacts extraction, and constructs context payloads
for LLM prompts so JEXI remembers details across sessions.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models.memory_fact import MemoryFact
from models.conversation import Conversation
from models.task import Task
from models.habit_log import HabitLog


class MemoryService:
    def __init__(self, db: Session):
        self.db = db

    def save_fact(self, user_id: int, key: str, value: str, auto_extracted: bool = False):
        """Upsert a memory fact."""
        try:
            fact = self.db.query(MemoryFact).filter_by(user_id=user_id, key=key).first()
            if fact:
                fact.value = value
                fact.updated_at = datetime.now(timezone.utc)
            else:
                fact = MemoryFact(
                    user_id=user_id,
                    key=key,
                    value=value,
                    auto_extracted=auto_extracted
                )
                self.db.add(fact)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def get_fact(self, user_id: int, key: str) -> str | None:
        """Get single fact value."""
        try:
            fact = self.db.query(MemoryFact).filter_by(user_id=user_id, key=key).first()
            return fact.value if fact else None
        except Exception:
            return None

    def get_all_facts(self, user_id: int) -> dict:
        """Return all facts as {key: value} map."""
        try:
            facts = self.db.query(MemoryFact).filter_by(user_id=user_id).all()
            return {f.key: f.value for f in facts}
        except Exception:
            return {}

    def delete_fact(self, user_id: int, key: str):
        """Remove a fact."""
        try:
            fact = self.db.query(MemoryFact).filter_by(user_id=user_id, key=key).first()
            if fact:
                self.db.delete(fact)
                self.db.commit()
        except Exception:
            self.db.rollback()

    def save_message(
        self, user_id: int, session_id: str, role: str, content: str,
        provider: str = None, model: str = None, response_time: float = None
    ):
        """Save a message to Conversation history."""
        try:
            msg = Conversation(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                provider=provider,
                model=model,
                response_time=response_time
            )
            self.db.add(msg)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def get_conversation(self, user_id: int, session_id: str, limit: int = 20) -> list:
        """Get last N messages for a session, ordered oldest to newest."""
        try:
            messages = (
                self.db.query(Conversation)
                .filter_by(user_id=user_id, session_id=session_id)
                .order_by(desc(Conversation.created_at))
                .limit(limit)
                .all()
            )
            # Re-reverse so oldest is first
            return [{"role": m.role, "content": m.content} for m in reversed(messages)]
        except Exception:
            return []

    def clear_conversation(self, user_id: int, session_id: str):
        """Delete all messages for a session."""
        try:
            self.db.query(Conversation).filter_by(user_id=user_id, session_id=session_id).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()

    async def auto_extract_facts(self, user_id: int, text: str) -> list:
        """Uses LLM to extract {key, value} facts from user text and saves them."""
        try:
            prompt = (
                "Extract personal facts from this text. Return ONLY a valid JSON array of {key, value} pairs. "
                "Examples: [{'key': 'name', 'value': 'Alex'}, {'key': 'age', 'value': '22'}]. "
                "Only extract clear facts. Return empty array '[]' if none found. Text: " + text
            )
            from services.llm_router import get_llm_router
            llm_router = get_llm_router()
            resp = await llm_router.route([{"role": "user", "content": prompt}])
            
            # Extract JSON from response
            text_resp = resp.get("text", "")
            start = text_resp.find("[")
            end = text_resp.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            
            facts = json.loads(text_resp[start:end])
            for f in facts:
                if "key" in f and "value" in f:
                    self.save_fact(user_id, str(f["key"]), str(f["value"]), auto_extracted=True)
            return facts
        except Exception:
            return []

    def build_context(self, user_id: int, session_id: str) -> dict:
        """Gather ALL context for AI prompt injection."""
        try:
            context = {}
            # 1. Facts
            facts = self.get_all_facts(user_id)
            context["facts"] = "\n".join(f"- {k}: {v}" for k, v in facts.items())
            
            # 2. Today's Date/Time
            now = datetime.now(timezone.utc)
            context["datetime"] = now.isoformat()
            
            # 3. Tasks
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            pending_tasks = self.db.query(Task).filter(Task.user_id == user_id, Task.status != "done").count()
            completed_tasks = self.db.query(Task).filter(
                Task.user_id == user_id, 
                Task.status == "done",
                Task.completed_at >= today_start
            ).count()
            context["tasks_summary"] = f"{pending_tasks} pending, {completed_tasks} completed today"
            
            # 4. Habits
            total_habits = 0  # Logic depends on daily habit query
            done_habits = self.db.query(HabitLog).filter(
                HabitLog.date == today_start.date(),
                HabitLog.habit.has(user_id=user_id),
                HabitLog.completed == True
            ).count()
            context["habits_summary"] = f"{done_habits} habits completed today"

            # 5. Conversations
            context["recent_messages"] = self.get_conversation(user_id, session_id, limit=20)
            
            return context
        except Exception:
            return {}
