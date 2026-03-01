from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta

from auth import get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_delete

router = APIRouter(prefix="/api/v1/learning", tags=["Learning"])

class LearningNoteCreate(BaseModel):
    content: str
    topic: Optional[str] = None
    tags: Optional[str] = None
    source: Optional[str] = None

class LearningNoteUpdate(BaseModel):
    content: Optional[str] = None
    topic: Optional[str] = None
    tags: Optional[str] = None
    next_review_date: Optional[date] = None

@router.get("/notes")
async def list_notes(user_id: int = Depends(get_current_user)):
    try:
        notes = sb_select("learning_notes", filters={"user_id": user_id})
        return notes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notes")
async def create_note(note_data: LearningNoteCreate, user_id: int = Depends(get_current_user)):
    try:
        data = note_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        # Set initial review date to tomorrow
        data["next_review_date"] = (date.today() + timedelta(days=1)).isoformat()
        result = sb_insert("learning_notes", data)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/review-due")
async def list_review_due(user_id: int = Depends(get_current_user)):
    try:
        # Simple fetch and filter by date
        notes = sb_select("learning_notes", filters={"user_id": user_id})
        today = date.today()
        due = [n for n in notes if n.get("next_review_date") and date.fromisoformat(n["next_review_date"]) <= today]
        return due
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/notes/{note_id}/reviewed")
async def mark_reviewed(note_id: int, user_id: int = Depends(get_current_user)):
    try:
        # Get current note
        rows = sb_select("learning_notes", filters={"id": note_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Note not found")
        
        note = rows[0]
        review_count = note.get("review_count", 0) + 1
        
        # Simple Spaced Repetition Logic (Exponential backoff)
        # 1, 2, 4, 8, 16... days
        days_to_add = 2 ** review_count
        next_date = (date.today() + timedelta(days=days_to_add)).isoformat()
        
        update_data = {
            "review_count": review_count,
            "next_review_date": next_date
        }
        
        result = sb_update("learning_notes", "id", note_id, update_data)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz/generate")
async def generate_quiz(data: dict, user_id: int = Depends(get_current_user)):
    topic = data.get("topic", "")
    # Placeholder for AI quiz generation
    # In a real scenario, this would call LLM provider with note context
    return [
        {
            "question": f"What is the core concept of {topic}?",
            "correct_answer": f"The fundamental principle of {topic} as noted in your Zettelkasten."
        },
        {
            "question": f"How does {topic} relate to your previous notes?",
            "correct_answer": "It forms a node in your personal knowledge graph, connecting theoretical concepts to practical applications."
        }
    ]

@router.get("/courses")
async def list_courses(user_id: int = Depends(get_current_user)):
    try:
        courses = sb_select("learning_courses", filters={"user_id": user_id})
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
