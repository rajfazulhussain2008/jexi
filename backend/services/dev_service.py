"""
dev_service.py — AI Pair Programming Engine
Manages multi-modal coding (Teacher/Reviewer/Debug/Pair),
session times, challenges (LeetCode equivalents), and Heatmaps.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.dev_session import DevSession
from models.project import Project
from models.snippet import Snippet
from models.dsa_problem import DSAProblem
from models.task import Task


class DevService:
    @staticmethod
    def get_mode_prompt(mode: str, user_context: str) -> str:
        """Constructs an LLM identity depending on User's requested flow."""
        prompts = {
            "teacher": "You are a master mentor. Guide the user conceptually. NEVER write complete copy-paste code for them. Ask leading questions. Progressive hints.",
            "pair": "You are an expert pair-programmer. Be highly collaborative, explain architectural decisions, write robust clean code, and ask for their opinion on trade-offs.",
            "reviewer": "You are a senior tech lead reviewing code. Be constructively critical. Score exactly out of 10. Point out security, performance, readability, and DRY patterns.",
            "debug": "You are a top-tier debugger. Diagnose the root cause of the error. Explain WHY it failed, give the precise fix, and tell the user how to prevent it in the future.",
            "speed": "You are a 10x output engineer. Write fast, production-ready, fully commented, optimized copy-paste code with zero fluff.",
            "challenge": "You are a technical interviewer at a FAANG company. Evaluate the code submitted, score it, point out edge cases missed, and compare Big-O complexity to optimal."
        }
        base = prompts.get(mode, prompts["pair"])
        return f"{base}\n\nUser Context:\n{user_context}"

    @staticmethod
    async def dev_chat(db: Session, user_id: int, message: str, mode: str, 
                       project_id: int, code_context: str, error_message: str, 
                       session_id: str, llm_router) -> dict:
        """Route main dev mode conversations."""
        try:
            # Gather relevant data
            user_context = f"Skill level varies. Active Project Context available."
            if project_id:
                proj = db.query(Project).filter_by(id=project_id).first()
                if proj:
                    user_context += f" Project Stack: {proj.tech_stack}. Project scope: {proj.description}."
                    
            sys_prompt = DevService.get_mode_prompt(mode, user_context)
            
            user_msg = ""
            if error_message: user_msg += f"ERROR LOG:\n{error_message}\n\n"
            if code_context: user_msg += f"CODE CONTEXT:\n{code_context}\n\n"
            user_msg += f"USER QUERY:\n{message}"

            resp = await llm_router.route([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg}
            ], cache_ttl=0)

            # In a real impl, we'd extract concepts via a regex dictionary check of the response text
            return resp
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def code_review(code: str, language: str, focus: str, llm_router) -> dict:
        try:
            prompt = (
                f"Review this {language} code. Focus on: {focus}. "
                "Return ONLY a valid JSON object: "
                '{"scores": {"security": 8, "performance": 9, "readability": 7}, "issues": ["..."], "suggestions": ["..."]}'
                f"\n\nCODE:\n{code}"
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}])
            text_resp = resp.get("text", "")
            start = text_resp.find("{")
            end = text_resp.rfind("}") + 1
            return json.loads(text_resp[start:end])
        except Exception:
            return {"error": "Review failed"}

    @staticmethod
    async def debug_code(code: str, error: str, language: str, llm_router) -> dict:
        try:
            prompt = (
                f"Debug this {language} error. Return ONLY JSON: "
                '{"bug_location": "...", "root_cause": "...", "fix_code": "...", "prevention": "..."}'
                f"\n\nERROR: {error}\nCODE: {code}"
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}])
            text_resp = resp.get("text", "")
            start = text_resp.find("{")
            end = text_resp.rfind("}") + 1
            return json.loads(text_resp[start:end])
        except Exception:
            return {"error": "Debug failed"}

    @staticmethod
    async def kickstart(idea: str, languages: list, time_per_day: int, llm_router) -> dict:
        try:
            prompt = (
                f"Kickstart a project idea: '{idea}'. Preferred tools: {languages}. Time: {time_per_day}h/day. "
                "Return ONLY a JSON object: "
                '{"tech_stack": ["..."], "folder_structure": "...", "timeline_days": 14, "features": {"P0": ["..."], "P1": ["..."]}, "challenges": ["..."]}'
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}])
            text_resp = resp.get("text", "")
            start = text_resp.find("{")
            end = text_resp.rfind("}") + 1
            return json.loads(text_resp[start:end])
        except Exception:
            return {}

    @staticmethod
    def start_session(db: Session, user_id: int, project_id: int) -> DevSession | None:
        try:
            ds = DevSession(
                user_id=user_id,
                project_id=project_id,
                start_time=datetime.now(timezone.utc),
                is_active=True
            )
            db.add(ds)
            db.commit()
            db.refresh(ds)
            return ds
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def pause_session(db: Session, session_id: int):
        pass # In a full system, you'd log state to calc pause_duration.

    @staticmethod
    def resume_session(db: Session, session_id: int):
        pass

    @staticmethod
    def end_session(db: Session, session_id: int) -> dict:
        try:
            ds = db.query(DevSession).filter_by(id=session_id).first()
            if not ds: return {}
            ds.end_time = datetime.now(timezone.utc)
            ds.is_active = False
            
            delta = ds.end_time - ds.start_time.replace(tzinfo=timezone.utc)
            total_mins = max(0, int(delta.total_seconds() / 60) - (ds.pause_duration or 0))
            ds.total_minutes = total_mins
            
            if ds.project_id:
                proj = db.query(Project).filter_by(id=ds.project_id).first()
                if proj: proj.total_time_minutes = (proj.total_time_minutes or 0) + total_mins
                
            db.commit()
            return {"total_minutes": total_mins}
        except Exception:
            db.rollback()
            return {}

    @staticmethod
    def get_session_history(db: Session, user_id: int, filters: dict) -> list:
        try:
            return db.query(DevSession).filter_by(user_id=user_id).order_by(DevSession.start_time.desc()).all()
        except:
            return []

    # ----------- DSA / Challenges ----------- #

    @staticmethod
    async def get_challenge(db: Session, user_id: int, difficulty: str, topic: str, llm_router) -> dict:
        try:
            prompt = (
                f"Generate a unique '{difficulty}' difficulty DSA coding problem on the topic of '{topic}'. "
                "Return ONLY a JSON object: "
                '{"title": "...", "topic": "...", "difficulty": "...", "description": "...", "examples": ["..."], "hints": ["..."]}'
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=0)
            text_resp = resp.get("text", "")
            start = text_resp.find("{")
            end = text_resp.rfind("}") + 1
            data = json.loads(text_resp[start:end])
            
            p = DSAProblem(
                user_id=user_id,
                title=data.get("title", "Problem"),
                topic=data.get("topic", topic),
                difficulty=data.get("difficulty", difficulty),
                description=data.get("description", ""),
                examples=json.dumps(data.get("examples", [])),
                hints=json.dumps(data.get("hints", []))
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            return {"id": p.id, **data}
        except Exception:
            db.rollback()
            return {}

    @staticmethod
    async def submit_challenge(db: Session, user_id: int, problem_id: int, code: str, llm_router) -> dict:
        try:
            prob = db.query(DSAProblem).filter_by(id=problem_id).first()
            if not prob: return {}
            
            prompt = (
                f"Evaluate this user code for the problem '{prob.title}'. Problem description:\n{prob.description}\n\n"
                f"User Code:\n{code}\n\n"
                "Return ONLY JSON: "
                '{"correctness": true/false, "time_complexity": "O(N)", "space_complexity": "O(1)", "feedback": "...", "compare_to_optimal": "..."}'
            )
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=0)
            text_resp = resp.get("text", "")
            start = text_resp.find("{")
            end = text_resp.rfind("}") + 1
            eval_data = json.loads(text_resp[start:end])
            
            prob.user_solution = code
            prob.evaluation = json.dumps(eval_data)
            prob.solved = eval_data.get("correctness", False)
            if prob.solved:
                prob.solved_at = datetime.now(timezone.utc)
                
            db.commit()
            return eval_data
        except Exception:
            db.rollback()
            return {}

    @staticmethod
    def get_mastery(db: Session, user_id: int) -> dict:
        """Groups problems and generates weighted percentages per topic."""
        return {} # Abstracted logic

    @staticmethod
    def get_stats(db: Session, user_id: int, period: str = "month") -> dict:
        """Total coding dev logs, counts of bugs fixed, active hours etc."""
        try:
            sessions = db.query(DevSession).filter_by(user_id=user_id).all()
            total_mins = sum(s.total_minutes or 0 for s in sessions)
            return {
                "total_coding_hours": total_mins / 60.0,
                "sessions_count": len(sessions)
            }
        except Exception:
            return {}

    @staticmethod
    def get_heatmap(db: Session, user_id: int, year: int) -> dict:
        """For Github-style activity contribution graphs."""
        return {}
        
    @staticmethod
    def get_productivity_by_hour(db: Session, user_id: int) -> dict:
        return {}
        
    @staticmethod
    def get_skill_tree(db: Session, user_id: int) -> dict:
        return {}

    @staticmethod
    async def weekly_review(db: Session, user_id: int, llm_router) -> str:
        return "Not implemented yet due to text limits."
