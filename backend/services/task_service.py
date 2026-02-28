"""
task_service.py — Task management
Handles CRUD for Tasks, plus AI breakdown and generation.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from models.task import Task


class TaskService:
    @staticmethod
    def create(db: Session, user_id: int, data: dict) -> Task | None:
        """Create a task from data dict."""
        try:
            task = Task(
                user_id=user_id,
                title=data.get("title"),
                description=data.get("description"),
                priority=data.get("priority", "medium"),
                status=data.get("status", "pending"),
                due_date=data.get("due_date"),
                category=data.get("category"),
                project_id=data.get("project_id"),
                goal_id=data.get("goal_id"),
                estimated_time=data.get("estimated_time"),
                tags=json.dumps(data.get("tags", [])),
                subtasks=json.dumps(data.get("subtasks", []))
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_all(db: Session, user_id: int, filters: dict = None) -> list[Task]:
        """Query with filters."""
        try:
            query = db.query(Task).filter(Task.user_id == user_id)
            if not filters:
                return query.all()

            if "status" in filters:
                query = query.filter(Task.status == filters["status"])
            if "priority" in filters:
                query = query.filter(Task.priority == filters["priority"])
            if "category" in filters:
                query = query.filter(Task.category == filters["category"])
            if "project_id" in filters:
                query = query.filter(Task.project_id == filters["project_id"])
            if "goal_id" in filters:
                query = query.filter(Task.goal_id == filters["goal_id"])
            
            sort_by = filters.get("sort_by", "created_at")
            if sort_by == "due_date":
                query = query.order_by(asc(Task.due_date))
            elif sort_by == "priority":
                query = query.order_by(Target.priority)
            else:
                query = query.order_by(desc(Task.created_at))

            if "limit" in filters:
                query = query.limit(filters["limit"])
            if "offset" in filters:
                query = query.offset(filters["offset"])

            return query.all()
        except Exception:
            return []

    @staticmethod
    def get_by_id(db: Session, user_id: int, task_id: int) -> Task | None:
        try:
            return db.query(Task).filter_by(id=task_id, user_id=user_id).first()
        except Exception:
            return None

    @staticmethod
    def update(db: Session, user_id: int, task_id: int, data: dict) -> Task | None:
        """Update task and handle side-effects."""
        try:
            task = TaskService.get_by_id(db, user_id, task_id)
            if not task:
                return None

            for key, value in data.items():
                if hasattr(task, key):
                    if key in ["tags", "subtasks"] and isinstance(value, list):
                        setattr(task, key, json.dumps(value))
                    else:
                        setattr(task, key, value)

            if task.status == "done" and not task.completed_at:
                task.completed_at = datetime.now(timezone.utc)
            elif task.status != "done":
                task.completed_at = None

            db.commit()
            db.refresh(task)
            return task
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def delete(db: Session, user_id: int, task_id: int) -> bool:
        try:
            task = TaskService.get_by_id(db, user_id, task_id)
            if task:
                db.delete(task)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False

    @staticmethod
    async def ai_create(db: Session, user_id: int, natural_text: str, llm_router) -> dict | None:
        """Parse natural language into a Task object via LLM."""
        try:
            prompt = (
                "Parse this into a task. Return ONLY valid JSON: "
                '{"title": "", "description": "", "priority": "high/medium/low", '
                '"due_date": "YYYY-MM-DDTHH:MM:SSZ or null", "category": "", "estimated_time": int_minutes}. Text: '
                + natural_text
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
    async def ai_breakdown(db: Session, user_id: int, task_description: str, llm_router) -> list:
        """Break down a task into subtasks via LLM."""
        try:
            prompt = (
                "Break this task into actionable subtasks. Return ONLY a valid JSON array of objects: "
                '[{"title": "...", "estimated_minutes": 15}]. Task: ' + task_description
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=0)
            text_resp = resp.get("text", "")
            start = text_resp.find("[")
            end = text_resp.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            return json.loads(text_resp[start:end])
        except Exception:
            return []

    @staticmethod
    def get_today(db: Session, user_id: int, llm_router=None) -> list[Task]:
        """Get prioritized tasks for today."""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            tasks = db.query(Task).filter(
                Task.user_id == user_id,
                Task.status != "done",
                or_(Task.due_date == None, Task.due_date >= today_start)
            ).order_by(asc(Task.due_date)).all()
            return tasks
        except Exception:
            return []

    @staticmethod
    def get_overdue(db: Session, user_id: int) -> list[Task]:
        """Get overdue tasks."""
        try:
            now = datetime.now(timezone.utc)
            return db.query(Task).filter(
                Task.user_id == user_id,
                Task.status != "done",
                Task.due_date < now
            ).all()
        except Exception:
            return []

    @staticmethod
    def get_stats(db: Session, user_id: int, period: str = "week") -> dict:
        """Task completion statistics."""
        try:
            # Simplistic stats logic for now
            total = db.query(Task).filter_by(user_id=user_id).count()
            completed = db.query(Task).filter_by(user_id=user_id, status="done").count()
            pending = db.query(Task).filter(Task.user_id == user_id, Task.status != "done").count()
            overdue = len(TaskService.get_overdue(db, user_id))
            rate = round(completed / total, 2) if total > 0 else 0.0

            return {
                "total": total,
                "completed": completed,
                "pending": pending,
                "overdue": overdue,
                "completion_rate": rate,
                "avg_completion_time": 0 # TODO calculate avg difference between created_at and completed_at
            }
        except Exception:
            return {}
