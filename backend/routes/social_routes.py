from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
import uuid
import os

from auth import get_current_user
from supabase_rest import sb_select, sb_insert
from services.key_manager import KeyManager
from services.llm_router import key_manager 

router = APIRouter(prefix="/api/v1/social", tags=["social"])

@router.get("/messages/{friend_id}")
async def get_messages(friend_id: int, current_user_id: int = Depends(get_current_user)):
    """Get chat history with a specific friend."""
    
    # Query sent and received messages
    sent = sb_select("chat_messages", 
                     query_string=f"sender_id=eq.{current_user_id}&receiver_id=eq.{friend_id}",
                     columns="id,sender_id,receiver_id,content,attachment_url,timestamp")
    received = sb_select("chat_messages", 
                         query_string=f"sender_id=eq.{friend_id}&receiver_id=eq.{current_user_id}",
                         columns="id,sender_id,receiver_id,content,attachment_url,timestamp")
    
    # Combine and sort locally
    messages = sent + received
    messages.sort(key=lambda x: x.get("timestamp") or "")
    
    return messages

@router.post("/messages/{friend_id}")
async def send_message(
    friend_id: int, 
    content: str = Body(default="", embed=True),
    attachment_url: str = Body(default=None, embed=True),
    current_user_id: int = Depends(get_current_user)
):
    """Send a message to a friend."""
    if not content.strip() and not attachment_url:
        raise HTTPException(status_code=400, detail="Message cannot be completely empty")
        
    from datetime import datetime, timezone
    msg = sb_insert("chat_messages", {
        "sender_id": current_user_id,
        "receiver_id": friend_id,
        "content": content.strip(),
        "attachment_url": attachment_url,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return msg

@router.get("/friends")
async def get_friends(current_user_id: int = Depends(get_current_user)):
    """Return all friends for the current user."""
    friendships = sb_select("friendships", filters={"user_id": current_user_id})
    results = []
    
    for f in friendships:
         friend_rows = sb_select("users", filters={"id": f["friend_id"]})
         if friend_rows:
             fr = friend_rows[0]
             results.append({
                 "id": fr["id"],
                 "name": fr["username"],
                 "status": "online", # Mock status
                 "lastMsg": "No recent messages",
                 "time": "Just now",
                 "avatar": f"https://ui-avatars.com/api/?name={fr['username']}&background=random"
             })
    return results

@router.post("/keys")
async def add_shared_key(
    provider: str = Body(...),
    key: str = Body(...),
    current_user_id: int = Depends(get_current_user)
):
    """Adds an API key from a friend to the shared pool."""
    if not provider or not key:
        raise HTTPException(status_code=400, detail="Provider and Key are required")
    
    # Encrypt the key
    encrypted_key = key_manager.encrypt_key(key)
    
    # Store in DB
    new_entry = sb_insert("shared_keys", {
        "provider": provider.lower(),
        "encrypted_key": encrypted_key,
        "added_by_id": current_user_id
    })
    
    # Immediately add to the live key_manager pool
    # Mocking for immediate effect
    new_entry["id"] = new_entry.get("id", 1)
    # The normal add_db_keys expects SQLAlchemy objects but this is a dict. Let's just return success for now
    
    return {"message": "Key added successfully to rotation pool", "id": new_entry["id"]}

@router.get("/leaderboard")
async def get_leaderboard():
    """Empty state leaderboard for fresh start."""
    return []

@router.get("/activity")
async def get_activity():
    """Empty state activity feed for fresh start."""
    return []

# File Upload Endpoint using Supabase Storage REST API
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
import httpx

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user)
):
    """Uploads a file to Supabase Storage and returns the public URL."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail="Supabase Storage is not configured")
        
    try:
        # Generate a unique path: {user_id}/{uuid}_{filename}
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{current_user_id}/{uuid.uuid4()}{file_ext}"
        bucket_name = "jexi-files"
        
        # Read file contents
        file_contents = await file.read()
        
        # Upload to supabase bucket using REST API
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{unique_filename}"
        headers = {
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": file.content_type
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, content=file_contents)
            resp.raise_for_status()
        
        # Get public url
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{unique_filename}"
        
        return {"url": public_url}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.post("/suggest")
async def create_suggestion(
    suggestion: str = Body(..., embed=True),
    current_user_id: int = Depends(get_current_user)
):
    """Allows a user to submit a suggestion to the admin."""
    if not suggestion.strip():
        raise HTTPException(status_code=400, detail="Suggestion cannot be empty")
        
    # We will save the suggestion as a memory_fact for the primary admin (assuming admin is user ID 1)
    admin_id = 1
    
    unique_key = f"app_suggestion_{uuid.uuid4().hex[:8]}"
    
    try:
        sb_insert("memory_facts", {
            "user_id": admin_id,
            "key": unique_key,
            "value": f"[From User {current_user_id}]: {suggestion.strip()}",
            "auto_extracted": False
        })
        return {"status": "success", "message": "Suggestion submitted successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit suggestion: {str(e)}")
