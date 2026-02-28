"""
goal_service.py — Goal tracking and tracking algorithm
Hierarchies, Risk pace calculation, and AI generation/narratives.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from models.goal import Goal


class GoalService:
    @staticmethod
    def create(db: Session, user_id: int, data: dict) -> Goal | None:
        try:
            goal = Goal(
                user_id=user_id,
                title=data.get("title"),
                description=data.get("description"),
                goal_type=data.get("goal_type", "monthly"),
                target_value=data.get("target_value", 100.0),
                current_value=data.get("current_value", 0.0),
                deadline=data.get("deadline"),
                parent_goal_id=data.get("parent_goal_id"),
                category=data.get("category"),
                milestones=json.dumps(data.get("milestones", [])),
                status=data.get("status", "active")
            )
            db.add(goal)
            db.commit()
            db.refresh(goal)
            return goal
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_all(db: Session, user_id: int, filters: dict = None) -> list[Goal]:
        try:
            query = db.query(Goal).filter_by(user_id=user_id)
            if filters:
                if "status" in filters:
                    query = query.filter_by(status=filters["status"])
                if "goal_type" in filters:
                    query = query.filter_by(goal_type=filters["goal_type"])
            return query.all()
        except Exception:
            return []

    @staticmethod
    def get_by_id(db: Session, user_id: int, goal_id: int) -> Goal | None:
        try:
            return db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
        except Exception:
            return None

    @staticmethod
    def update(db: Session, user_id: int, goal_id: int, data: dict) -> Goal | None:
        try:
            goal = GoalService.get_by_id(db, user_id, goal_id)
            if not goal:
                return None
            for k, v in data.items():
                if hasattr(goal, k):
                    if k == "milestones" and isinstance(v, list):
                        setattr(goal, k, json.dumps(v))
                    else:
                        setattr(goal, k, v)
            db.commit()
            db.refresh(goal)
            return goal
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def delete(db: Session, user_id: int, goal_id: int) -> bool:
        try:
            goal = GoalService.get_by_id(db, user_id, goal_id)
            if goal:
                db.delete(goal)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def get_hierarchy(db: Session, user_id: int) -> dict:
        """Build tree structure: life -> yearly -> quarterly -> monthly -> weekly"""
        try:
            goals = GoalService.get_all(db, user_id)
            goals_dict = {g.id: {
                "id": g.id, "title": g.title, "type": g.goal_type, 
                "progress": (g.current_value / g.target_value * 100) if g.target_value else 0,
                "children": []
            } for g in goals}

            roots = []
            for g in goals:
                if g.parent_goal_id and g.parent_goal_id in goals_dict:
                    goals_dict[g.parent_goal_id]["children"].append(goals_dict[g.id])
                else:
                    roots.append(goals_dict[g.id])
            return {"hierarchy": roots}
        except Exception:
            return {}

    @staticmethod
    def get_at_risk(db: Session, user_id: int) -> list:
        """Find goals lagging behind the required pace to meet deadline."""
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None) # Ensure naive for comparison
            goals = db.query(Goal).filter_by(user_id=user_id, status="active").all()
            at_risk = []
            for g in goals:
                if not g.deadline or not g.target_value or g.target_value == 0:
                    continue
                # Ensure naive tz
                deadline_naive = g.deadline.replace(tzinfo=None)
                created_naive = g.created_at.replace(tzinfo=None) if g.created_at else now

                total_days = (deadline_naive - created_naive).days
                if total_days <= 0:
                    continue
                
                days_rem = (deadline_naive - now).days
                days_elapsed = total_days - days_rem
                if days_rem <= 0:
                    at_risk.append({"goal": g.title, "risk": "Failed/Expired"})
                    continue
                
                required_pace = (g.target_value - g.current_value) / days_rem
                # Simple protection against Div/0
                actual_pace = g.current_value / (days_elapsed if days_elapsed > 0 else 1)

                if actual_pace < required_pace * 0.8:
                    at_risk.append({
                        "id": g.id,
                        "title": g.title,
                        "required_pace": round(required_pace, 2),
                        "actual_pace": round(actual_pace, 2),
                        "days_remaining": days_rem
                    })
            return at_risk
        except Exception:
            return []

    @staticmethod
    async def ai_suggest(db: Session, user_id: int, llm_router) -> list:
        """Ask LLM to suggest 3 new goals based on current ones."""
        try:
            goals = db.query(Goal).filter_by(user_id=user_id).all()
            titles = [g.title for g in goals]
            prompt = (
                f"User's current goals: {', '.join(titles)}. "
                "Suggest 3 new SMART goals based on common self-improvement gaps. "
                "Return ONLY a valid JSON array of strings. Example: ['Read 10 pages daily', 'Code 1 hr']."
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}])
            text_resp = resp.get("text", "")
            try:
                # Find array
                start = text_resp.find("[")
                end = text_resp.rfind("]") + 1
                return json.loads(text_resp[start:end])
            except:
                return []
        except Exception:
            return []

    @staticmethod
    async def get_progress_report(db: Session, user_id: int, llm_router) -> str:
        """A narrative progress report."""
        try:
            goals = db.query(Goal).filter_by(user_id=user_id, status="active").all()
            if not goals:
                return "You have no active goals."
            
            data = [f"- {g.title}: {g.current_value}/{g.target_value} ({g.goal_type})" for g in goals]
            prompt = (
                "Write an encouraging, objective narrative progress report based on these goals:\n"
                + "\n".join(data) + "\nKeep it strictly under 3 paragraphs."
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=3600)
            return resp.get("text", "Error generating report.")
        except Exception:
            return "Could not generate progress report right now."
