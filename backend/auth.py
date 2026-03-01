from datetime import datetime, timedelta, timezone

from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
import bcrypt
import uuid
from supabase_rest import sb_select

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    # Ensure it doesn't exceed 72 bytes to prevent bcrypt ValueError
    pw_bytes = password.encode('utf-8')[:72]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        pw_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception as e:
        print(f"Bcrypt verification error: {e}")
        return False


def create_token(data: dict) -> str:
    """Create a JWT token with an expiry claim and a unique JTI."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def is_session_valid(jti: str) -> bool:
    """Check if the session JTI has been revoked in the database."""
    try:
        rows = sb_select("sessions", filters={"token_jti": jti})
        if not rows:
            print(f"DEBUG: JTI {jti} not found in database. Allowing for legacy/sync.")
            return True 
        
        session = rows[0]
        status = not session.get("is_revoked", False)
        print(f"DEBUG: JTI {jti} validation status: {status} (is_revoked: {session.get('is_revoked')})")
        return status
    except Exception as e:
        print(f"DEBUG: Session check CRITICAL FAILURE for JTI {jti}: {e}")
        return True # Fail open



def verify_token(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns the payload or None on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(request: Request) -> int:
    """
    FastAPI dependency — extracts the Bearer token from the Authorization
    header, verifies it, and returns the user_id.
    Raises HTTP 401 if the token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user_id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    # Only check session revocation if a JTI is present in the token
    if jti:
        if not is_session_valid(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return user_id
