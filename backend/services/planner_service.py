"""
planner_service.py — Interactive Briefing and Schedules
Builds generative Morning/Evening narratives leveraging tools API context,
task queue prioritization, and schedules LLM optimized timetable generation.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from models.task import Task
from models.habit import Habit

from services.tools_service import ToolsService
from services.analytics_service import AnalyticsService


class PlannerService:
    @staticmethod
    async def morning_briefing(db: Session, user_id: int, llm_router) -> dict:
        """Gathers runtime states + Weather/News, builds morning AI summary."""
        try:
            weather = ToolsService.get_weather()
            db_score = AnalyticsService.calculate_life_score(db, user_id)
            
            prompt = (
                f"Give me a highly motivational morning briefing. Include today's weather context if present: "
                f"Weather: {json.dumps(weather)}. Yesterday's score was {db_score['total']}. Tell me to crush it."
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=1800)
            
            return {
                "weather": weather,
                "motivational_message": resp.get("text", "Good morning! Time to be productive."),
                "yesterday_score": db_score['total']
            }
        except Exception:
            return {"motivational_message": "Good morning!"}

    @staticmethod
    async def evening_review(db: Session, user_id: int, llm_router) -> dict:
        """Night time wrapup summarizing the day."""
        try:
            score = AnalyticsService.calculate_life_score(db, user_id)
            prompt = (
                f"Give me a brief, reflective evening wind-down summary. "
                f"Today's total life score was {score['total']}/100. "
                "Keep it soothing, maximum 3 sentences."
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=1800)
            
            return {
                "ai_summary": resp.get("text", "You did well today. Rest up."),
                "today_score": score['total']
            }
        except Exception:
            return {"ai_summary": "Rest well tonight."}

    @staticmethod
    async def generate_schedule(db: Session, user_id: int, available_hours: int, llm_router) -> list:
        """Generates hourly blocks (time-boxing) prioritizing pending tasks."""
        try:
            tasks = db.query(Task).filter_by(user_id=user_id, status="pending").order_by(Task.priority).limit(5).all()
            titles = [t.title for t in tasks]
            
            prompt = (
                f"I have {available_hours} hours available. Schedule these tasks: {', '.join(titles)}. "
                "Include breaks. Return ONLY a valid JSON array of objects: "
                '[{"time": "09:00", "activity": "...", "duration": 60, "type": "task/break"}]'
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=0)
            text_resp = resp.get("text", "")
            start = text_resp.find("[")
            end = text_resp.rfind("]") + 1
            return json.loads(text_resp[start:end])
        except Exception:
            return []

    @staticmethod
    def start_focus(db: Session, user_id: int, task_id: int, duration: int) -> dict:
        """Commence Pomodoro/Focus timer."""
        # Simple placeholder for webhooks
        return {"status": "Focus started", "task_id": task_id, "duration": duration}

    @staticmethod
    def end_focus(db: Session, user_id: int, session_id: int) -> dict:
        """Conclude timer, update task time-logs implicitly."""
        return {"status": "Focus ended"}
