from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_delete

router = APIRouter(prefix="/api/v1/health", tags=["Health"])

class HealthLogCreateUpdate(BaseModel):
    date: str
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None
    water_liters: Optional[float] = None
    steps: Optional[int] = None
    exercise_type: Optional[str] = None
    exercise_duration: Optional[int] = None
    meals_logged: Optional[int] = None
    weight: Optional[float] = None
    notes: Optional[str] = None

@router.get("/score")
async def health_score(user_id: int = Depends(get_current_user)):
    return {"total": 85}

@router.get("/today")
async def get_today_health(user_id: int = Depends(get_current_user)):
    from datetime import date
    today = date.today().isoformat()
    try:
        logs = sb_select("health_logs", filters={"user_id": user_id, "date": today})
        if not logs:
            return None
        return logs[0]
    except Exception as e:
        return None

@router.post("/log")
async def log_health_metrics(log_data: HealthLogCreateUpdate, user_id: int = Depends(get_current_user)):
    try:
        data = log_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        
        existing = sb_select("health_logs", filters={"user_id": user_id, "date": data["date"]})
        
        if existing:
            result = sb_update("health_logs", "id", existing[0]["id"], data)
        else:
            result = sb_insert("health_logs", data)
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def health_trends(metric: str = "sleep_hours", user_id: int = Depends(get_current_user)):
    try:
        logs = sb_select("health_logs", filters={"user_id": user_id})
        logs.sort(key=lambda x: x["date"])
        return [{"date": l["date"], "value": l.get(metric, 0)} for l in logs]
    except Exception as e:
        return []

@router.get("/ai-insights")
async def health_ai_insights(user_id: int = Depends(get_current_user)):
    return "Your sleep quality improves on days you drink more than 2 liters of water. However, focus on increasing your activity on weekends."

@router.get("/logs")
async def list_health_logs(user_id: int = Depends(get_current_user)):
    try:
        logs = sb_select("health_logs", filters={"user_id": user_id})
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/{date}")
async def get_health_log(date: str, user_id: int = Depends(get_current_user)):
    try:
        logs = sb_select("health_logs", filters={"user_id": user_id, "date": date})
        if not logs:
            return {"status": "success", "data": None}
        return {"status": "success", "data": logs[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logs")
async def save_health_log(log_data: HealthLogCreateUpdate, user_id: int = Depends(get_current_user)):
    try:
        data = log_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        
        existing = sb_select("health_logs", filters={"user_id": user_id, "date": data["date"]})
        
        if existing:
            # Update
            result = sb_update("health_logs", "id", existing[0]["id"], data)
        else:
            # Insert
            result = sb_insert("health_logs", data)
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/logs/{log_id}")
async def delete_health_log(log_id: int, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("health_logs", filters={"id": log_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Log not found")
            
        sb_delete("health_logs", "id", log_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
