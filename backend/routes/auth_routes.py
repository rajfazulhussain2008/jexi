# ---------- routes/auth_routes.py ----------
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from auth import hash_password, verify_password, create_token, get_current_user
from models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# ── Pydantic schemas ──────────────────────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    username: str


# ── Routes ────────────────────────────────────────────────────────
@router.post("/setup")
async def setup(body: AuthRequest, db: Session = Depends(get_db)):
    """First-time setup — create the initial user. Allowed only once."""
    try:
        existing = db.query(User).first()
        if existing:
            raise HTTPException(status_code=400, detail="Setup already completed. Use /login.")

        user = User(
            username=body.username,
            hashed_password=hash_password(body.password),
            is_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_token({"user_id": user.id, "username": user.username, "is_admin": user.is_admin})
        return {
            "status": "success",
            "data": {"token": token, "username": user.username, "is_admin": user.is_admin},
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/login")
async def login(body: AuthRequest, db: Session = Depends(get_db)):
    """Authenticate with username + password, receive a JWT."""
    try:
        user = db.query(User).filter(User.username == body.username).first()
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_token({"user_id": user.id, "username": user.username, "is_admin": user.is_admin})
        return {
            "status": "success",
            "data": {"token": token, "username": user.username, "is_admin": user.is_admin},
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/me")
async def me(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current user's profile from the token."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "status": "success",
            "data": {
                "id": user.id,
                "username": user.username,
                "is_admin": user.is_admin,
                "created_at": str(user.created_at),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/logout")
async def logout(user_id: int = Depends(get_current_user)):
    """Logout — client should discard the token."""
    return {"status": "success", "data": {"message": "Logged out"}}
