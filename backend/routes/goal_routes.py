from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_delete

router = APIRouter(prefix="/api/v1/goals", tags=["Goals"])

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    goal_type: str
    target_value: Optional[float] = None
    current_value: Optional[float] = 0.0
    deadline: Optional[str] = None
    parent_goal_id: Optional[int] = None
    category: Optional[str] = None
    milestones: Optional[str] = None
    status: Optional[str] = "active"

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    milestones: Optional[str] = None

@router.get("")
async def list_goals(user_id: int = Depends(get_current_user)):
    try:
        goals = sb_select("goals", filters={"user_id": user_id})
        return goals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_goal(goal_data: GoalCreate, user_id: int = Depends(get_current_user)):
    try:
        data = goal_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        result = sb_insert("goals", data)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hierarchy")
async def goal_hierarchy(user_id: int = Depends(get_current_user)):
    try:
        goals = sb_select("goals", filters={"user_id": user_id})
        # Simple flat list as hierarchy for now
        return goals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai-suggest")
async def goal_ai_suggest(user_id: int = Depends(get_current_user)):
    return ["Break your 'Learn Python' goal into 5 smaller sub-goals.", "You usually finish health goals faster in the morning."]

@router.get("/at-risk")
async def goal_at_risk(user_id: int = Depends(get_current_user)):
    # Returns empty list or mocked risks
    return []

@router.get("/progress-report")
async def goal_progress_report(user_id: int = Depends(get_current_user)):
    return "You've completed 20% of your yearly goals. Your strongest area is 'Learning'."

@router.get("/{goal_id}")
async def get_goal(goal_id: int, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("goals", filters={"id": goal_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Goal not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{goal_id}")
async def update_goal_put(goal_id: int, goal_data: dict, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("goals", filters={"id": goal_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        result = sb_update("goals", "id", goal_id, goal_data)
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{goal_id}")
async def delete_goal(goal_id: int, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("goals", filters={"id": goal_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Goal not found")
            
        sb_delete("goals", "id", goal_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
