from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from supabase_rest import sb_select, sb_update, sb_delete


router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(user_id: int = Depends(get_current_user)):
    """Fetch unread notifications for the user."""
    try:
        notes = sb_select("notifications", filters={"user_id": user_id})
        return notes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{notification_id}/read")
async def mark_as_read(notification_id: int, user_id: int = Depends(get_current_user)):
    """Mark a notification as read."""
    try:
        sb_update("notifications", "id", notification_id, {"is_read": True})
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notification_id}")
async def delete_notification(notification_id: int, user_id: int = Depends(get_current_user)):
    """Delete a notification."""
    try:
        sb_delete("notifications", "id", notification_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
