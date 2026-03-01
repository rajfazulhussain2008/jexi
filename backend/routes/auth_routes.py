# ---------- routes/auth_routes.py ----------
"""
Auth routes using Supabase REST API (HTTP-based).
This bypasses psycopg2/SQLAlchemy and works on Vercel serverless functions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import hash_password, verify_password, create_token, get_current_user, verify_token
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
async def setup(body: AuthRequest, request: Request):
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(body: AuthRequest, request: Request):
    """Authenticate with username + password and log the event."""
    client_ip = request.client.host if request.client else "unknown"
    client_ua = request.headers.get("user-agent", "unknown")

    try:
        # SECURITY CHECK: Fail-open brute force protection
        try:
            # Check for recent failures (Basic Rate Limiting/Anti-Brute Force)
            # Check if this IP has > 5 failures in the last 5 minutes
            five_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            # Clean isoformat (remove +00:00 and use Z) for PostgREST compatibility
            clean_ts = five_mins_ago.replace("+00:00", "Z")
            
            # Use query_string with manual encoding for the timestamp
            fail_count = sb_count("security_logs", 
                                query_string=f"event_type=eq.login_failed&ip_address=eq.{client_ip}&created_at=gt.{clean_ts}")
            
            if fail_count >= 10:
                # Log the lockout attempt
                try:
                    sb_insert("security_logs", {
                        "event_type": "rate_limit_lockout",
                        "ip_address": client_ip,
                        "user_agent": client_ua,
                        "details": f"IP {client_ip} strictly blocked after {fail_count} failed tries."
                    })
                except: pass
                raise HTTPException(status_code=429, detail="Too many failed attempts. Please try again in 5 minutes.")
        except HTTPException:
            raise
        except Exception as e:
            print(f"SECURITY CHECK WARNING: Brute force check failed: {e}")
            # We continue even if check fails to prevent system-wide lockout due to DB issues

        rows = sb_select("users", filters={"username": body.username})
        
        if not rows:
            # Audit the failure
            try:
                sb_insert("security_logs", {
                    "event_type": "login_failed",
                    "ip_address": client_ip,
                    "user_agent": client_ua,
                    "details": f"Attempt for non-existent user: {body.username}"
                })
            except: pass
            raise HTTPException(status_code=401, detail="Invalid username or password")

        user = rows[0]
        if not verify_password(body.password, user["hashed_password"]):
            # Audit the failure
            try:
                sb_insert("security_logs", {
                    "user_id": user["id"],
                    "event_type": "login_failed",
                    "ip_address": client_ip,
                    "user_agent": client_ua,
                    "details": "Incorrect password"
                })
            except: pass
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Success - Generate Token
        token = create_token({
            "user_id": user["id"],
            "username": user["username"],
            "is_admin": user["is_admin"]
        })

        # Audit the success
        try:
            sb_insert("security_logs", {
                "user_id": user["id"],
                "event_type": "login_success",
                "ip_address": client_ip,
                "user_agent": client_ua,
                "details": f"Authenticated via Web on {client_ua[:30]}..."
            })
        except: pass

        # Register Active Session
        # Extract JTI from the token we just made
        payload = verify_token(token)
        jti = payload.get("jti")
        
        try:
            sb_insert("sessions", {
                "user_id": user["id"],
                "token_jti": jti,
                "ip_address": client_ip,
                "user_agent": client_ua,
                "is_revoked": False
            })
        except Exception as e:
            print(f"SESSION REGISTRATION ERROR: {e}")

        # Create a notification for the user about the new login
        try:
            sb_insert("notifications", {
                "user_id": user["id"],
                "type": "warning",
                "title": "New Login Detected",
                "message": f"A new device logged into your JEXI account.\n\n📍 IP: {client_ip}\n📱 Device: {client_ua[:50]}...",
                "action_url": "/settings"
            })
        except: pass

        return {
            "status": "success",
            "data": {"token": token, "username": user["username"], "is_admin": user["is_admin"]},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/sessions")
async def list_active_sessions(user_id: int = Depends(get_current_user)):
    """List all active (non-revoked) sessions for the current user."""
    try:
        sessions = sb_select("sessions", filters={"user_id": user_id, "is_revoked": False})
        return {"status": "success", "data": sessions}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(session_id: int, user_id: int = Depends(get_current_user)):
    """Remote logout: Revoke a specific session."""
    try:
        # Check ownership
        rows = sb_select("sessions", filters={"id": session_id, "user_id": user_id})
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sb_update("sessions", "id", session_id, {"is_revoked": True})
        
        return {"status": "success", "message": "Session revoked. That device will be logged out on next request."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/logout-all")
async def logout_all_devices(user_id: int = Depends(get_current_user)):
    """Revoke ALL sessions for the current user."""
    try:
        # Note: sb_update by filter column is simple, but Supabase/PostgREST allows mass updates
        # For safety/simplicity in this helper, we fetch and loop or use raw if we had it
        sessions = sb_select("sessions", filters={"user_id": user_id, "is_revoked": False})
        for s in sessions:
            sb_update("sessions", "id", s["id"], {"is_revoked": True})
            
        return {"status": "success", "message": "All sessions revoked. Re-login required on all devices."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
