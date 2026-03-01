from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_delete

router = APIRouter(prefix="/api/v1/finance", tags=["Finance"])

class TransactionCreate(BaseModel):
    amount: float
    type: str
    category: str
    description: Optional[str] = None
    date: str
    payment_method: Optional[str] = None
    is_recurring: Optional[bool] = False
    recurring_frequency: Optional[str] = None

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    payment_method: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurring_frequency: Optional[str] = None

@router.get("/summary")
async def finance_summary(period: str = "month", user_id: int = Depends(get_current_user)):
    try:
        txs = sb_select("transactions", filters={"user_id": user_id})
        income = sum([t["amount"] for t in txs if t["type"] == "income"])
        expenses = sum([t["amount"] for t in txs if t["type"] == "expense"])
        
        # Category breakdown
        breakdown = {}
        for t in txs:
            if t["type"] == "expense":
                cat = t["category"]
                breakdown[cat] = breakdown.get(cat, 0) + t["amount"]
        
        breakdown_list = [{"category": k, "amount": v} for k, v in breakdown.items()]
        
        return {
            "total_income": income,
            "total_expenses": expenses,
            "net_savings": income - expenses,
            "category_breakdown": breakdown_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/budgets/status")
async def budget_status(user_id: int = Depends(get_current_user)):
    # Mocking budget status for now
    return [
        {"category": "Food", "spent_amount": 150, "budget_amount": 300, "percentage_used": 50},
        {"category": "Rent", "spent_amount": 1200, "budget_amount": 1200, "percentage_used": 100}
    ]

@router.post("/ai-parse")
async def ai_parse_finance(data: dict, user_id: int = Depends(get_current_user)):
    # Placeholder for AI parsing
    text = data.get("text", "")
    return {
        "amount": 15.50,
        "type": "expense",
        "category": "food",
        "description": f"AI Parsed: {text[:30]}"
    }

@router.get("/transactions")
async def list_transactions(user_id: int = Depends(get_current_user)):
    try:
        transactions = sb_select("transactions", filters={"user_id": user_id})
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transactions")
async def create_transaction(tx_data: TransactionCreate, user_id: int = Depends(get_current_user)):
    try:
        data = tx_data.dict(exclude_unset=True)
        data["user_id"] = user_id
        result = sb_insert("transactions", data)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/transactions/{tx_id}")
async def update_transaction(tx_id: int, tx_data: TransactionUpdate, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("transactions", filters={"id": tx_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        data = tx_data.dict(exclude_unset=True)
        if not data:
            return {"status": "success", "data": rows[0]}

        result = sb_update("transactions", "id", tx_id, data)
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/transactions/{tx_id}")
async def delete_transaction(tx_id: int, user_id: int = Depends(get_current_user)):
    try:
        rows = sb_select("transactions", filters={"id": tx_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        sb_delete("transactions", "id", tx_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
