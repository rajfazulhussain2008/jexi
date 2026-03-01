from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict
from datetime import date, timedelta
import random

from auth import get_current_user
from supabase_rest import sb_select

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.get("/life-score")
async def get_life_score(user_id: int = Depends(get_current_user)):
    try:
        # Fetch stats from various tables to calculate a composite score
        tasks = sb_select("tasks", filters={"user_id": user_id})
        habits = sb_select("habits", filters={"user_id": user_id})
        habit_logs = sb_select("habit_logs", filters={"user_id": user_id})
        health_logs = sb_select("health_logs", filters={"user_id": user_id})
        goals = sb_select("goals", filters={"user_id": user_id})
        
        # Simple weighted scoring logic
        task_score = min(20, len([t for t in tasks if t.get("status") == "done"]) * 2) if tasks else 10
        habit_score = min(20, len(habit_logs) * 2) if habit_logs else 10
        health_score = 15 # Stub
        goal_score = min(20, len([g for g in goals if g.get("status") == "completed"]) * 5) if goals else 10
        coding_score = 15 # Stub
        
        total = task_score + habit_score + health_score + goal_score + coding_score
        
        return {
            "total": total,
            "breakdown": {
                "tasks": task_score,
                "habits": habit_score,
                "health": health_score,
                "goals": goal_score,
                "coding": coding_score
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/life-score/history")
async def get_life_score_history(period: int = 30, user_id: int = Depends(get_current_user)):
    # Stub: Generate some fake historical data for the chart
    history = []
    base_score = 65
    today = date.today()
    for i in range(period, -1, -1):
        d = today - timedelta(days=i)
        score = base_score + random.randint(-10, 15)
        history.append({
            "date": d.isoformat(),
            "total_score": max(0, min(100, score))
        })
    return history

@router.get("/ai-insights")
async def get_ai_insights(user_id: int = Depends(get_current_user)):
    # Placeholder for AI correlation analysis
    return [
        "Your productivity (tasks done) increases by 25% when you log at least 7.5 hours of sleep.",
        "Financial spending in 'Entertainment' correlates with lower 'Focus' scores the following day.",
        "Morning meditation habits have a 0.82 correlation with goal progress this month."
    ]

@router.post("/weekly-review")
async def generate_weekly_review(user_id: int = Depends(get_current_user)):
    # Placeholder for LLM generated weekly summary
    return "This week you achieved 85% of your primary goals. Your focus was highest on Tuesday. Recommendation: Increase deep work blocks on Thursdays."
