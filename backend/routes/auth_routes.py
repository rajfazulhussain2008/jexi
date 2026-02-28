# ---------- routes/auth_routes.py ----------
"""
Auth routes using Supabase REST API (HTTP-based).
This bypasses psycopg2/SQLAlchemy and works on Vercel serverless functions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import hash_password, verify_password, create_token, get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_count

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# ── Pydantic schemas ──────────────────────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str
    admin_secret: str


# ── Routes ────────────────────────────────────────────────────────
@router.post("/setup")
async def setup(body: AuthRequest):
    """First-time setup — create the ONLY/initial admin account."""
    try:
        # Check if any user already exists
        existing_count = sb_count("users")
        if existing_count > 0:
            raise HTTPException(status_code=400, detail="Setup already completed. Use /login.")

        # Create the admin user
        new_user = sb_insert("users", {
            "username": body.username,
            "hashed_password": hash_password(body.password),
            "is_admin": True,
        })

        token = create_token({
            "user_id": new_user["id"],
            "username": new_user["username"],
            "is_admin": new_user["is_admin"]
        })
        return {
            "status": "success",
            "data": {"token": token, "username": new_user["username"], "is_admin": new_user["is_admin"]},
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/login")
async def login(body: AuthRequest):
    """Authenticate with username + password, receive a JWT."""
    try:
        rows = sb_select("users", filters={"username": body.username})
        if not rows:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = rows[0]
        if not verify_password(body.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_token({
            "user_id": user["id"],
            "username": user["username"],
            "is_admin": user["is_admin"]
        })
        return {
            "status": "success",
            "data": {"token": token, "username": user["username"], "is_admin": user["is_admin"]},
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/me")
async def me(user_id: int = Depends(get_current_user)):
    """Return the current user's profile from the token."""
    try:
        rows = sb_select("users", filters={"id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="User not found")
        u = rows[0]
        return {
            "status": "success",
            "data": {
                "id": u["id"],
                "username": u["username"],
                "is_admin": u["is_admin"],
                "created_at": str(u.get("created_at", "")),
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


@router.get("/users")
async def list_users():
    """List all users — admin debugging endpoint."""
    try:
        users = sb_select("users", columns="id,username,is_admin,created_at")
        return {"status": "success", "data": users}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Reset a user's password. Uses JWT secret as admin_secret."""
    from config import JWT_SECRET
    if body.admin_secret != JWT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    rows = sb_select("users", filters={"username": body.username})
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")

    sb_update("users", "username", body.username, {
        "hashed_password": hash_password(body.new_password)
    })
    return {"status": "success", "data": {"message": f"Password reset for {body.username}"}}
