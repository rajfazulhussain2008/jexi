"""
project_service.py — Kanban, Workflows & Github-level Portfolios
Calculates velocity, deadlines, parses Devlogs from tasks, and runs auto-generation
for Markdown READMEs / Portfolio site summaries using the LLM router.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.project import Project
from models.task import Task


class ProjectService:
    @staticmethod
    def create(db: Session, user_id: int, data: dict) -> Project | None:
        try:
            p = Project(
                user_id=user_id,
                name=data.get("name"),
                description=data.get("description"),
                tech_stack=json.dumps(data.get("tech_stack", [])),
                status=data.get("status", "planning"),
                deadline=data.get("deadline"),
                github_url=data.get("github_url"),
                goal_id=data.get("goal_id")
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            return p
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_all(db: Session, user_id: int) -> list:
        try:
            return db.query(Project).filter_by(user_id=user_id).all()
        except Exception:
            return []

    @staticmethod
    def get_by_id(db: Session, user_id: int, project_id: int) -> Project | None:
        try:
            return db.query(Project).filter_by(id=project_id, user_id=user_id).first()
        except Exception:
            return None

    @staticmethod
    def update(db: Session, user_id: int, project_id: int, data: dict) -> Project | None:
        try:
            p = db.query(Project).filter_by(id=project_id, user_id=user_id).first()
            if not p: return None
            for k, v in data.items():
                if hasattr(p, k):
                    if k == "tech_stack" and isinstance(v, list):
                        setattr(p, k, json.dumps(v))
                    else:
                        setattr(p, k, v)
            db.commit()
            db.refresh(p)
            return p
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def delete(db: Session, user_id: int, project_id: int) -> bool:
        try:
            p = db.query(Project).filter_by(id=project_id, user_id=user_id).first()
            if p:
                db.delete(p)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def get_board(db: Session, user_id: int, project_id: int) -> dict:
        """Get kanban-structured tasks."""
        try:
            tasks = db.query(Task).filter_by(user_id=user_id, project_id=project_id).all()
            res = {"todo": [], "in_progress": [], "review": [], "done": []}
            for t in tasks:
                if t.status in res: res[t.status].append(t)
                else: res["todo"].append(t)
            return res
        except Exception:
            return {"todo": [], "in_progress": [], "review": [], "done": []}

    @staticmethod
    def move_task(db: Session, user_id: int, project_id: int, task_id: int, new_status: str):
        """Move task, update parent project progress logic."""
        try:
            task = db.query(Task).filter_by(id=task_id, user_id=user_id, project_id=project_id).first()
            if not task: return

            task.status = new_status
            if new_status == "done":
                task.completed_at = datetime.now(timezone.utc)
            else:
                task.completed_at = None

            # Calculate if Project is done
            all_tasks = db.query(Task).filter_by(user_id=user_id, project_id=project_id).all()
            total = len(all_tasks)
            done = sum(1 for t in all_tasks if t.status == "done")
            
            if total > 0 and done == total:
                proj = db.query(Project).filter_by(id=project_id).first()
                if proj: proj.status = "completed"
                
            db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def get_devlog(db: Session, user_id: int, project_id: int) -> list:
        """History of completed tasks by date."""
        try:
            tasks = db.query(Task).filter(
                Task.user_id == user_id, 
                Task.project_id == project_id, 
                Task.status == "done",
                Task.completed_at != None
            ).order_by(desc(Task.completed_at)).all()
            
            # Group by ISO date
            log_dict = {}
            for t in tasks:
                date_str = str(t.completed_at.date()) if t.completed_at else "Unknown"
                if date_str not in log_dict:
                    log_dict[date_str] = {"date": date_str, "tasks": [], "hours_spent": 0}
                log_dict[date_str]["tasks"].append(t.title)
                log_dict[date_str]["hours_spent"] += (t.estimated_time or 0) / 60.0
                
            return list(log_dict.values())
        except Exception:
            return []

    @staticmethod
    def get_health(db: Session, user_id: int, project_id: int) -> dict:
        """Progress trackers, Velocity, Deadlines."""
        try:
            proj = db.query(Project).filter_by(id=project_id, user_id=user_id).first()
            if not proj: return {}
            
            tasks = db.query(Task).filter_by(user_id=user_id, project_id=project_id).all()
            total = len(tasks)
            done = sum(1 for t in tasks if t.status == "done")
            rem = total - done
            
            # Extremely basic velocity: completed tasks total
            # Realistic system uses trailing 7 days -> left as 'total done' over time
            velocity = done / 7.0 if done > 0 else 0
            
            est_days = rem / velocity if velocity > 0 else 999
            
            risk = "low"
            if proj.deadline:
                days_left = (proj.deadline.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
                if est_days > days_left: risk = "high"
                
            return {
                "progress": (done / total * 100) if total else 0,
                "velocity": round(velocity, 2),
                "remaining_tasks": rem,
                "estimated_days": round(est_days, 1),
                "deadline_risk": risk
            }
        except Exception:
            return {}

    @staticmethod
    async def generate_readme(db: Session, user_id: int, project_id: int, llm_router) -> str:
        """Call LLM to auto-auth complete README.md."""
        try:
            proj = db.query(Project).filter_by(id=project_id, user_id=user_id).first()
            stack = proj.tech_stack or "[]"
            board = ProjectService.get_board(db, user_id, project_id)
            done_titles = [t.title for t in board["done"]]
            
            prompt = (
                f"Write a professional GitHub README.md for this project:\n"
                f"Name: {proj.name}\nDescription: {proj.description}\nTech: {stack}\n"
                f"Completed Features: {', '.join(done_titles)}\n"
                "Include Sections: Title, Description, Features, Tech Stack, Installation. Format strictly in Markdown."
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=0)
            return resp.get("text", "# Project README\nError generating.")
        except Exception:
            return "Generation failed."

    @staticmethod
    async def generate_portfolio_entry(db: Session, user_id: int, project_id: int, llm_router) -> dict:
        """Return JSON structured portfolio data."""
        try:
            proj = db.query(Project).filter_by(id=project_id, user_id=user_id).first()
            prompt = (
                f"Generate a portfolio showcase object for: Name={proj.name}, Tech={proj.tech_stack}, Desc={proj.description}. "
                "Return ONLY a JSON object: "
                '{"title": "...", "description": "...", "features": ["..."], "tech_stack": ["..."], "highlights": ["..."]}'
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=0)
            text_resp = resp.get("text", "")
            try:
                start = text_resp.find("{")
                end = text_resp.rfind("}") + 1
                return json.loads(text_resp[start:end])
            except:
                return {}
        except Exception:
            return {}
