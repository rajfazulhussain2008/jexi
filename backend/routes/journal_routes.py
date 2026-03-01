from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_delete

router = APIRouter(prefix="/api/v1/journal", tags=["Journal"])

class JournalEntryCreateUpdate(BaseModel):
    date: str
    content: Optional[str] = None
    mood_score: Optional[int] = None
    energy_score: Optional[int] = None
    tags: Optional[str] = None
    gratitude: Optional[str] = None
    wins: Optional[str] = None
    challenges: Optional[str] = None
    tomorrow_intention: Optional[str] = None
    ai_analysis: Optional[str] = None

@router.get("")
async def list_journal_entries(user_id: int = Depends(get_current_user)):
    try:
        entries = sb_select("journal_entries", filters={"user_id": user_id})
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/today")
async def get_today_journal(user_id: int = Depends(get_current_user)):
    from datetime import date
    today = date.today().isoformat()
    try:
        entries = sb_select("journal_entries", filters={"user_id": user_id, "date": today})
        if not entries:
            return None
        return entries[0]
    except Exception as e:
        return None

@router.post("/log")
async def log_journal_entry(entry_data: JournalEntryCreateUpdate, user_id: int = Depends(get_current_user)):
    try:
        data = entry_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        
        existing = sb_select("journal_entries", filters={"user_id": user_id, "date": data["date"]})
        
        if existing:
            result = sb_update("journal_entries", "id", existing[0]["id"], data)
        else:
            result = sb_insert("journal_entries", data)
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_journal_entry(data: dict, user_id: int = Depends(get_current_user)):
    return {
        "sentiment": "Positive",
        "emotion": "Empowered",
        "distortions": [],
        "feedback": "Your journal shows strong progress in self-awareness. You mentioned several wins today which correlate with your high energy score."
    }

@router.get("/history")
async def journal_history(days: int = 14, user_id: int = Depends(get_current_user)):
    try:
        entries = sb_select("journal_entries", filters={"user_id": user_id})
        # Sort and limit in memory for now
        entries.sort(key=lambda x: x["date"], reverse=True)
        return entries[:days]
    except Exception as e:
        return []

@router.get("/{date}")
async def get_journal_entry(date: str, user_id: int = Depends(get_current_user)):
    try:
        entries = sb_select("journal_entries", filters={"user_id": user_id, "date": date})
        if not entries:
            return {"status": "success", "data": None}
        return {"status": "success", "data": entries[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def save_journal_entry(entry_data: JournalEntryCreateUpdate, user_id: int = Depends(get_current_user)):
    try:
        data = entry_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        
        # Check if entry exists for this date
        existing = sb_select("journal_entries", filters={"user_id": user_id, "date": data["date"]})
        
        if existing:
            # Update
            result = sb_update("journal_entries", "id", existing[0]["id"], data)
        else:
            # Insert
            result = sb_insert("journal_entries", data)
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{entry_id}")
async def delete_journal_entry(entry_id: int, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("journal_entries", filters={"id": entry_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Entry not found")
            
        sb_delete("journal_entries", "id", entry_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
