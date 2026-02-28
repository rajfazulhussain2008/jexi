from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict

from database import get_db
from auth import get_current_user
from models.user import User
from models.shared_key import SharedKey
from services.key_manager import KeyManager

# We assume a global key_manager instance exists and is managed 
# (In a real app, this would be a dependency or global app state)
from services.llm_router import key_manager 

from models.friendship import Friendship
from models.chat_message import ChatMessage
from sqlalchemy import or_, and_

router = APIRouter(prefix="/api/v1/social", tags=["social"])

@router.get("/messages/{friend_id}")
async def get_messages(friend_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Get chat history with a specific friend."""
    messages = db.query(ChatMessage).filter(
        or_(
            and_(ChatMessage.sender_id == current_user_id, ChatMessage.receiver_id == friend_id),
            and_(ChatMessage.sender_id == friend_id, ChatMessage.receiver_id == current_user_id)
        )
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    return [
        {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": msg.content,
            "attachment_url": msg.attachment_url,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]

@router.post("/messages/{friend_id}")
async def send_message(
    friend_id: int, 
    content: str = Body(default="", embed=True),
    attachment_url: str = Body(default=None, embed=True),
    db: Session = Depends(get_db), 
    current_user_id: int = Depends(get_current_user)
):
    """Send a message to a friend."""
    if not content.strip() and not attachment_url:
        raise HTTPException(status_code=400, detail="Message cannot be completely empty")
        
    msg = ChatMessage(
        sender_id=current_user_id,
        receiver_id=friend_id,
        content=content.strip(),
        attachment_url=attachment_url
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "receiver_id": msg.receiver_id,
        "content": msg.content,
        "attachment_url": msg.attachment_url,
        "timestamp": msg.timestamp.isoformat()
    }

@router.get("/friends")
async def get_friends(db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Return all friends for the current user."""
    friendships = db.query(Friendship).filter(Friendship.user_id == current_user_id).all()
    results = []
    for f in friendships:
         friend = db.query(User).filter(User.id == f.friend_id).first()
         if friend:
             results.append({
                 "id": friend.id,
                 "name": friend.username,
                 "status": "online", # Mock status
                 "lastMsg": "No recent messages",
                 "time": "Just now",
                 "avatar": f"https://ui-avatars.com/api/?name={friend.username}&background=random"
             })
    return results

@router.post("/keys")
async def add_shared_key(
    provider: str = Body(...),
    key: str = Body(...),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    """Adds an API key from a friend to the shared pool."""
    if not provider or not key:
        raise HTTPException(status_code=400, detail="Provider and Key are required")
    
    # Encrypt the key
    encrypted_key = key_manager.encrypt_key(key)
    
    # Store in DB
    new_entry = SharedKey(
        provider=provider.lower(),
        encrypted_key=encrypted_key,
        added_by_id=current_user_id
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    # Immediately add to the live key_manager pool
    key_manager.add_db_keys([new_entry])
    
    return {"message": "Key added successfully to rotation pool", "id": new_entry.id}

@router.get("/leaderboard")
async def get_leaderboard(db: Session = Depends(get_db)):
    """Empty state leaderboard for fresh start."""
    return []

@router.get("/activity")
async def get_activity(db: Session = Depends(get_db)):
    """Empty state activity feed for fresh start."""
    return []

# File Upload Endpoint using Supabase Storage
from fastapi import UploadFile, File
import uuid
import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Initialize Supabase Admin client for server-side uploads
# We use the service role key to bypass RLS for uploads from the backend.
# In a true zero-trust setup, the client (browser) should upload directly 
# against an RLS-protected bucket, but passing through backend prevents exposing secrets initially.
supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase client for storage: {e}")

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user)
):
    """Uploads a file to Supabase Storage and returns the public URL."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase Storage is not configured")
        
    try:
        # Generate a unique path: {user_id}/{uuid}_{filename}
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{current_user_id}/{uuid.uuid4()}{file_ext}"
        bucket_name = "jexi-files"
        
        # Read file contents
        file_contents = await file.read()
        
        # Upload to supabase bucket
        # (Be sure the 'jexi-files' bucket exists and is set to Public)
        res = supabase.storage.from_(bucket_name).upload(
            file=file_contents,
            path=unique_filename,
            file_options={"content-type": file.content_type}
        )
        
        # Get public url
        public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
        
        return {"url": public_url}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
