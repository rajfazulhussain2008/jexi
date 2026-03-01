from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_delete

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    status: Optional[str] = "pending"
    due_date: Optional[str] = None
    category: Optional[str] = None
    estimated_time: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    category: Optional[str] = None
    estimated_time: Optional[int] = None

@router.get("")
async def list_tasks(user_id: int = Depends(get_current_user)):
    try:
        tasks = sb_select("tasks", filters={"user_id": user_id})
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_task(task_data: TaskCreate, user_id: int = Depends(get_current_user)):
    try:
        data = task_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        result = sb_insert("tasks", data)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def task_stats(user_id: int = Depends(get_current_user)):
    try:
        tasks = sb_select("tasks", filters={"user_id": user_id})
        total = len(tasks)
        completed = len([t for t in tasks if t.get("status") == "done"])
        pending = total - completed
        overdue = 0 # Simple stub
        return {"total": total, "completed": completed, "pending": pending, "overdue": overdue}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}")
async def get_task(task_id: int, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("tasks", filters={"id": task_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai-create")
async def ai_create_task(data: dict, user_id: int = Depends(get_current_user)):
    # Placeholder for actual AI parsing logic
    text = data.get("text", "")
    return {
        "title": f"AI: {text[:50]}",
        "priority": "medium",
        "due_date": None,
        "category": "other"
    }

@router.post("/ai-breakdown")
async def ai_breakdown_task(data: dict, user_id: int = Depends(get_current_user)):
    # Placeholder for actual AI breakdown logic
    return [
        {"title": "Breakdown step 1", "estimated_minutes": 15},
        {"title": "Breakdown step 2", "estimated_minutes": 30}
    ]

@router.put("/{task_id}")
async def update_task_put(task_id: int, task_data: dict, user_id: int = Depends(get_current_user)):
    try:
        # Verify ownership
        rows = sb_select("tasks", filters={"id": task_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        
        result = sb_update("tasks", "id", task_id, task_data)
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}")
async def delete_task(task_id: int, user_id: int = Depends(get_current_user)):
    try:
        # Verify ownership
        rows = sb_select("tasks", filters={"id": task_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
            
        sb_delete("tasks", "id", task_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
