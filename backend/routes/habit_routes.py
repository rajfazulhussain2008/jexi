from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_delete

router = APIRouter(prefix="/api/v1/habits", tags=["Habits"])

class HabitCreate(BaseModel):
    name: str
    icon: Optional[str] = "✅"
    frequency: Optional[str] = "daily"
    custom_days: Optional[str] = None
    target: Optional[str] = None
    reminder_time: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = "medium"

class HabitUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    frequency: Optional[str] = None
    custom_days: Optional[str] = None
    target: Optional[str] = None
    reminder_time: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("")
async def list_habits(user_id: int = Depends(get_current_user)):
    try:
        habits = sb_select("habits", filters={"user_id": user_id})
        return habits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_habit(habit_data: HabitCreate, user_id: int = Depends(get_current_user)):
    try:
        data = habit_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        result = sb_insert("habits", data)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/today")
async def list_habits_today(user_id: int = Depends(get_current_user)):
    try:
        habits = sb_select("habits", filters={"user_id": user_id, "is_active": True})
        # Mocking completed_today for each habit
        return [{"habit": h, "completed_today": False} for h in habits]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{habit_id}/check")
async def check_habit(habit_id: int, user_id: int = Depends(get_current_user)):
    return {"status": "success", "streak": 5, "milestone_reached": False}

@router.delete("/{habit_id}/check")
async def uncheck_habit(habit_id: int, user_id: int = Depends(get_current_user)):
    return {"status": "success"}

@router.get("/streaks")
async def habit_streaks(user_id: int = Depends(get_current_user)):
    try:
        habits = sb_select("habits", filters={"user_id": user_id})
        return [{"habit": h["name"], "streak": 3} for h in habits]
    except Exception as e:
        return []

@router.get("/ai-insights")
async def habit_ai_insights(user_id: int = Depends(get_current_user)):
    return "You're most consistent with your 'Morning Meditation'. Consider moving 'Reading' to after dinner to increase your streak."

@router.put("/{habit_id}")
async def update_habit_put(habit_id: int, habit_data: dict, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("habits", filters={"id": habit_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Habit not found")
        
        result = sb_update("habits", "id", habit_id, habit_data)
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{habit_id}")
async def delete_habit(habit_id: int, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("habits", filters={"id": habit_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Habit not found")
            
        sb_delete("habits", "id", habit_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
