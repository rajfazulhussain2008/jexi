from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List

from auth import get_current_user, hash_password
from supabase_rest import sb_select, sb_insert

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

class CreateUserRequest(BaseModel):
    username: str
    password: str

async def check_admin(user_id: int = Depends(get_current_user)):
    user_rows = sb_select("users", filters={"id": user_id})
    if not user_rows:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    user = user_rows[0]
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

@router.post("/users")
async def admin_create_user(
    body: CreateUserRequest,
    admin: dict = Depends(check_admin)
):
    """Admin only: Create a new user and add them as a friend to the admin."""
    # Check if user exists
    existing = sb_select("users", filters={"username": body.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create user
    new_user = sb_insert("users", {
        "username": body.username,
        "hashed_password": hash_password(body.password),
        "is_admin": False
    })
    
    # Automatically add as friend to the admin
    sb_insert("friendships", {"user_id": admin["id"], "friend_id": new_user["id"], "status": "accepted"})
    sb_insert("friendships", {"user_id": new_user["id"], "friend_id": admin["id"], "status": "accepted"})

    return {
        "status": "success",
        "message": f"User {new_user['username']} created and added as friend",
        "user_id": new_user["id"]
    }

@router.get("/users")
async def list_all_users(admin: dict = Depends(check_admin)):
    users = sb_select("users", columns="id,username,is_admin")
    return [{"id": u["id"], "username": u["username"], "is_admin": u.get("is_admin", False)} for u in users]
