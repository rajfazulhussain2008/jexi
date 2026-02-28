from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from database import get_db
from auth import get_current_user, hash_password
from models.user import User
from models.friendship import Friendship

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

class CreateUserRequest(BaseModel):
    username: str
    password: str

async def check_admin(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

@router.post("/users")
async def admin_create_user(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin)
):
    """Admin only: Create a new user and add them as a friend to the admin."""
    # Check if user exists
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create user
    new_user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Automatically add as friend to the admin
    f1 = Friendship(user_id=admin.id, friend_id=new_user.id, status="accepted")
    f2 = Friendship(user_id=new_user.id, friend_id=admin.id, status="accepted")
    db.add(f1)
    db.add(f2)
    db.commit()

    return {
        "status": "success",
        "message": f"User {new_user.username} created and added as friend",
        "user_id": new_user.id
    }

@router.get("/users", response_model=List[dict])
async def list_all_users(db: Session = Depends(get_db), admin: User = Depends(check_admin)):
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "is_admin": u.is_admin} for u in users]
