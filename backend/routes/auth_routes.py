# ---------- routes/auth_routes.py ----------
"""
Auth routes using Supabase REST API (HTTP-based).
This bypasses psycopg2/SQLAlchemy and works on Vercel serverless functions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import hash_password, verify_password, create_token, get_current_user
from supabase_rest import sb_select, sb_insert, sb_update, sb_count
from datetime import datetime, timezone, timedelta

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

        # Log initial setup
        sb_insert("security_logs", {
            "user_id": new_user["id"],
            "event_type": "account_setup",
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "details": "Admin account initialized"
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
async def login(body: AuthRequest, request: Request):
    """Authenticate with username + password and log the event."""
    client_ip = request.client.host if request.client else "unknown"
    client_ua = request.headers.get("user-agent", "unknown")

    try:
        # 1. Check for recent failures (Basic Rate Limiting/Anti-Brute Force)
        # Check if this IP has > 5 failures in the last 5 minutes
        five_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        fail_count = sb_count("security_logs", 
                            query_string=f"event_type=eq.login_failed&ip_address=eq.{client_ip}&created_at=gt.{five_mins_ago}")
        
        if fail_count >= 10:
             # Log the lockout attempt
             sb_insert("security_logs", {
                 "event_type": "rate_limit_lockout",
                 "ip_address": client_ip,
                 "user_agent": client_ua,
                 "details": f"IP {client_ip} strictly blocked after {fail_count} failed tries."
             })
             raise HTTPException(status_code=429, detail="Too many failed attempts. Please try again in 5 minutes.")

        rows = sb_select("users", filters={"username": body.username})
        
        if not rows:
            # Audit the failure (but don't reveal user doesn't exist to prevent enumeration)
            sb_insert("security_logs", {
                "event_type": "login_failed",
                "ip_address": client_ip,
                "user_agent": client_ua,
                "details": f"Attempt for non-existent user: {body.username}"
            })
            raise HTTPException(status_code=401, detail="Invalid username or password")

        user = rows[0]
        if not verify_password(body.password, user["hashed_password"]):
            # Audit the failure
            sb_insert("security_logs", {
                "user_id": user["id"],
                "event_type": "login_failed",
                "ip_address": client_ip,
                "user_agent": client_ua,
                "details": "Incorrect password"
            })
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Success - Generate Token
        token = create_token({
            "user_id": user["id"],
            "username": user["username"],
            "is_admin": user["is_admin"]
        })

        # Audit the success
        sb_insert("security_logs", {
            "user_id": user["id"],
            "event_type": "login_success",
            "ip_address": client_ip,
            "user_agent": client_ua,
            "details": "Authenticated via Web"
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
