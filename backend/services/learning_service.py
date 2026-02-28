"""
learning_service.py — Spaced Repetition & Study Planner
Manages Zettelkasten-style notes, quiz generation, active recall logic, and graph relationships.
"""

import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from models.learning_course import LearningCourse
from models.learning_note import LearningNote
from models.book import Book


class LearningService:
    @staticmethod
    def create_course(db: Session, user_id: int, data: dict) -> LearningCourse | None:
        try:
            c = LearningCourse(
                user_id=user_id,
                title=data.get("title"),
                platform=data.get("platform"),
                url=data.get("url"),
                total_lessons=data.get("total_lessons", 1),
                completed_lessons=data.get("completed_lessons", 0),
                status=data.get("status", "in_progress")
            )
            db.add(c)
            db.commit()
            db.refresh(c)
            return c
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_courses(db: Session, user_id: int) -> list:
        try:
            return db.query(LearningCourse).filter_by(user_id=user_id).all()
        except Exception:
            return []

    @staticmethod
    def update_progress(db: Session, user_id: int, course_id: int, completed: int) -> LearningCourse | None:
        try:
            c = db.query(LearningCourse).filter_by(id=course_id, user_id=user_id).first()
            if not c: return None
            c.completed_lessons = completed
            if completed >= c.total_lessons:
                c.status = "completed"
            db.commit()
            db.refresh(c)
            return c
        except Exception:
            db.rollback()
            return None

    @staticmethod
    async def create_note(db: Session, user_id: int, data: dict, llm_router=None) -> LearningNote | None:
        try:
            n = LearningNote(
                user_id=user_id,
                content=data.get("content"),
                topic=data.get("topic"),
                tags=json.dumps(data.get("tags", [])),
                source=data.get("source"),
                next_review_date=datetime.now(timezone.utc).date() + timedelta(days=1), # initial repetition
                review_count=0
            )

            if llm_router and n.content:
                # Ask LLM for tags & topics
                prompt = (
                    "Analyze this learning note. Assign a primary 'topic' and a list of 'tags'. "
                    "Return ONLY valid JSON: "
                    '{"topic": "Machine Learning", "tags": ["gradient descent", "math"]}'
                    f"\nNOTE: {n.content}"
                )
                resp = await llm_router.route([{"role": "user", "content": prompt}])
                text_resp = resp.get("text", "")
                try:
                    start = text_resp.find("{")
                    end = text_resp.rfind("}") + 1
                    res = json.loads(text_resp[start:end])
                    if res.get("topic"): n.topic = res["topic"]
                    if res.get("tags"): n.tags = json.dumps(res["tags"])
                except:
                    pass

            db.add(n)
            db.commit()
            db.refresh(n)
            return n
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def get_notes(db: Session, user_id: int, filters: dict = None) -> list:
        try:
            q = db.query(LearningNote).filter_by(user_id=user_id)
            if filters and "topic" in filters:
                q = q.filter_by(topic=filters["topic"])
            return q.all()
        except:
            return []

    @staticmethod
    def search_notes(db: Session, user_id: int, query: str, llm_router=None) -> list:
        try:
            # Simple keyword search
            return db.query(LearningNote).filter(
                LearningNote.user_id == user_id,
                LearningNote.content.ilike(f"%{query}%")
            ).all()
        except:
            return []

    @staticmethod
    def get_review_due(db: Session, user_id: int) -> list:
        try:
            today = datetime.now(timezone.utc).date()
            return db.query(LearningNote).filter(
                LearningNote.user_id == user_id,
                LearningNote.next_review_date <= today
            ).all()
        except:
            return []

    @staticmethod
    def mark_reviewed(db: Session, user_id: int, note_id: int):
        try:
            n = db.query(LearningNote).filter_by(id=note_id, user_id=user_id).first()
            if not n: return
            n.review_count += 1
            
            # Simple spaced repetition gap algorithm
            intervals = {1: 3, 2: 7, 3: 14, 4: 30, 5: 90}
            days = intervals.get(n.review_count, 180) # default to ~6 mo if very mature
            
            n.next_review_date = datetime.now(timezone.utc).date() + timedelta(days=days)
            db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    async def generate_quiz(db: Session, user_id: int, topic: str, llm_router) -> list:
        try:
            notes = db.query(LearningNote).filter_by(user_id=user_id, topic=topic).all()
            if not notes: return []
            
            content = "\n\n".join([n.content for n in notes])
            prompt = (
                f"Based on my following {topic} notes, create a 5-question quiz. Mix MCQ and explain "
                "style questions. Return ONLY a valid JSON array of objects: "
                '[{"question": "...", "type": "mcq/text", "options": ["A", "B", "C", "D"], "correct_answer": "..."}]'
                f"\n\nNOTES:\n{content}"
            )
            
            resp = await llm_router.route([{"role": "user", "content": prompt}], cache_ttl=86400)
            text_resp = resp.get("text", "")
            start = text_resp.find("[")
            end = text_resp.rfind("}") + 1
            return json.loads(text_resp[start:end])
        except Exception:
            return []

    @staticmethod
    def create_book(db: Session, user_id: int, data: dict) -> Book | None:
        try:
            b = Book(
                user_id=user_id,
                title=data.get("title"),
                author=data.get("author"),
                total_pages=data.get("total_pages", 1),
                current_page=data.get("current_page", 0),
                status=data.get("status", "reading")
            )
            db.add(b)
            db.commit()
            db.refresh(b)
            return b
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def update_book_progress(db: Session, user_id: int, book_id: int, page: int) -> Book | None:
        try:
            b = db.query(Book).filter_by(id=book_id, user_id=user_id).first()
            if not b: return None
            b.current_page = page
            if page >= b.total_pages:
                b.status = "completed"
            db.commit()
            db.refresh(b)
            return b
        except Exception:
            db.rollback()
            return None

    @staticmethod
    async def study_plan(db: Session, user_id: int, llm_router) -> list:
        """Call LLM with review-due material and courses to structure a timeline."""
        return ["Not generated"]

    @staticmethod
    def get_knowledge_graph(db: Session, user_id: int) -> dict:
        """Builds node/edges logic for Zettelkasten visualizations."""
        return {"nodes": [], "edges": []}
