"""
memory_service.py — AI Memory & Context Builder
Manages Conversation history, MemoryFacts extraction, and constructs context payloads
for LLM prompts using Supabase REST API instead of SQLAlchemy.
"""

import json
from datetime import datetime, timezone

from supabase_rest import sb_select, sb_insert, sb_update, sb_count


class MemoryService:
    def __init__(self, db=None):
        # We accept db for legacy compatibility with routes injects, but ignore it.
        pass

    def save_fact(self, user_id: int, key: str, value: str, auto_extracted: bool = False):
        """Upsert a memory fact."""
        try:
            old_facts = sb_select("memory_facts", query_string=f"user_id=eq.{user_id}&key=eq.{key}")
            if old_facts:
                sb_update("memory_facts", "id", old_facts[0]["id"], {
                    "value": value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
            else:
                sb_insert("memory_facts", {
                    "user_id": user_id,
                    "key": key,
                    "value": value,
                    "auto_extracted": auto_extracted
                })
        except Exception as e:
            print(f"Error saving fact: {e}")

    def get_fact(self, user_id: int, key: str) -> str | None:
        """Get single fact value."""
        try:
            facts = sb_select("memory_facts", query_string=f"user_id=eq.{user_id}&key=eq.{key}")
            return facts[0]["value"] if facts else None
        except Exception:
            return None

    def get_all_facts(self, user_id: int) -> dict:
        """Return all facts as {key: value} map."""
        try:
            facts = sb_select("memory_facts", filters={"user_id": user_id})
            return {f["key"]: f["value"] for f in facts}
        except Exception as e:
            print(f"Error getting facts: {e}")
            return {}

    def delete_fact(self, user_id: int, key: str):
        """Remove a fact. (Not implemented purely via REST since we don't have delete, ignore for now)"""
        pass

    def save_message(
        self, user_id: int, session_id: str, role: str, content: str,
        provider: str = None, model: str = None, response_time: float = None
    ):
        """Save a message to Conversation history."""
        try:
            sb_insert("conversations", {
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "provider": provider,
                "model": model,
                "response_time": response_time
            })
        except Exception as e:
            print(f"Failed to save message: {e}")

    def get_conversation(self, user_id: int, session_id: str, limit: int = 20) -> list:
        """Get last N messages for a session, ordered oldest to newest."""
        try:
            messages = sb_select("conversations", 
                                 query_string=f"user_id=eq.{user_id}&session_id=eq.{session_id}&order=created_at.desc&limit={limit}")
            return [{"role": m["role"], "content": m["content"]} for m in reversed(messages)]
        except Exception as e:
            print(f"Failed to get conversation: {e}")
            return []

    def clear_conversation(self, user_id: int, session_id: str):
        """Delete all messages for a session. Ignore for now since delete is missing in supabase_rest."""
        pass

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
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            # Approximation since REST count isn't fully robust with multiple filters sometimes
            context["tasks_summary"] = ""
            
            # 4. Habits
            context["habits_summary"] = ""

            # 5. Conversations
            context["recent_messages"] = self.get_conversation(user_id, session_id, limit=20)
            
            return context
        except Exception as e:
            print(f"Failed to build context: {e}")
            return {}
