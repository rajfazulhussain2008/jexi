# ---------- routes/ai_routes.py ----------
import asyncio
import uuid
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database import get_db
from auth import get_current_user
from config import ASSISTANT_NAME, USER_NAME

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


# ── Pydantic schemas ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    provider: Optional[str] = None
    mode: Optional[str] = "general"


class ProviderPriority(BaseModel):
    name: str
    priority: int


class PriorityUpdate(BaseModel):
    priorities: List[ProviderPriority]


class ProviderTestRequest(BaseModel):
    provider: str


# ── Helper: detect tool triggers ──────────────────────────────────
TOOL_TRIGGERS = {
    "weather": "weather",
    "news": "news",
    "time": "time",
    "date": "time",
    "quote": "quote",
    "motivat": "quote",
    "joke": "joke",
    "funny": "joke",
    "wiki": "wiki",
    "who is": "wiki",
    "what is": "wiki",
}


def detect_tool(message: str) -> Optional[str]:
    lower = message.lower()
    for trigger, tool_name in TOOL_TRIGGERS.items():
        if trigger in lower:
            return tool_name
    return None


# ── Routes ────────────────────────────────────────────────────────
@router.post("/chat")
async def chat(
    body: ChatRequest,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to the AI assistant."""
    try:
        from services.llm_router import get_llm_router
        from services.memory_service import MemoryService
        from services.tools_service import ToolsService
        from models.conversation import Conversation

        llm_router = get_llm_router()
        memory_svc = MemoryService(db)
        tools_svc = ToolsService()

        session_id = body.session_id or str(uuid.uuid4())
        start_time = time.time()

        # Build context from memory
        context = memory_svc.build_context(user_id, session_id)

        # Check for tool triggers
        tool_result = None
        detected_tool = detect_tool(body.message)
        if detected_tool:
            try:
                if detected_tool == "weather":
                    tool_result = await tools_svc.get_weather()
                elif detected_tool == "news":
                    tool_result = await tools_svc.get_news()
                elif detected_tool == "time":
                    tool_result = f"Current date and time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                elif detected_tool == "quote":
                    tool_result = await tools_svc.get_quote()
                elif detected_tool == "joke":
                    tool_result = await tools_svc.get_joke()
                elif detected_tool == "wiki":
                    # Extract search query
                    q = body.message.lower().replace("who is", "").replace("what is", "").replace("wiki", "").strip()
                    tool_result = await tools_svc.get_wiki(q)
            except Exception:
                tool_result = None

        # Build system prompt
        now = datetime.now(timezone.utc)
        system_parts = [
            f"You are {ASSISTANT_NAME}, a personal AI Life OS assistant for {USER_NAME}.",
            f"Today is {now.strftime('%A, %B %d, %Y')}.",
            "Be helpful, concise, and proactive. Offer actionable advice.",
        ]
        if context.get("facts"):
            system_parts.append(f"User facts: {context['facts']}")
        if tool_result:
            system_parts.append(f"Tool result to incorporate: {tool_result}")

        system_prompt = "\n".join(system_parts)

        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        history = context.get("history", [])
        for msg in history[-20:]:  # Last 20 messages for context
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": body.message})

        # Route to LLM
        result = await llm_router.route(
            messages=messages,
            preferred_provider=body.provider,
        )

        response_time = time.time() - start_time

        # Save user message
        user_msg = Conversation(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=body.message,
        )
        db.add(user_msg)

        # Save assistant response
        assistant_msg = Conversation(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=result["text"],
            provider=result.get("provider"),
            model=result.get("model"),
            response_time=response_time,
        )
        db.add(assistant_msg)
        db.commit()

        # Auto-extract facts in background (don't block response)
        try:
            asyncio.create_task(
                _auto_extract_facts(user_id, body.message, memory_svc)
            )
        except Exception:
            pass  # Don't fail the response

        return {
            "status": "success",
            "data": {
                "text": result["text"],
                "provider": result.get("provider"),
                "model": result.get("model"),
                "response_time": round(response_time, 2),
                "session_id": session_id,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _auto_extract_facts(user_id, message, memory_svc):
    """Background task to extract facts from user messages."""
    try:
        await memory_svc.auto_extract_facts(user_id, message)
    except Exception:
        pass


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream a chat response using Server-Sent Events."""
    try:
        from services.llm_router import get_llm_router
        from services.memory_service import MemoryService
        from models.conversation import Conversation

        llm_router = get_llm_router()
        memory_svc = MemoryService(db)

        session_id = body.session_id or str(uuid.uuid4())

        # Build context
        context = memory_svc.build_context(user_id, session_id)

        now = datetime.now(timezone.utc)
        system_prompt = (
            f"You are {ASSISTANT_NAME}, a personal AI Life OS assistant for {USER_NAME}.\n"
            f"Today is {now.strftime('%A, %B %d, %Y')}.\n"
            "Be helpful, concise, and proactive."
        )
        if context.get("facts"):
            system_prompt += f"\nUser facts: {context['facts']}"

        messages = [{"role": "system", "content": system_prompt}]
        history = context.get("history", [])
        for msg in history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": body.message})

        async def event_generator():
            full_response = ""
            try:
                async for chunk in llm_router.stream(messages=messages, provider=body.provider):
                    full_response += chunk
                    yield f"data: {chunk}\n\n"
            except Exception:
                # Fallback: fake streaming by sending word-by-word
                result = await llm_router.route(messages=messages, preferred_provider=body.provider)
                words = result["text"].split(" ")
                for word in words:
                    full_response += word + " "
                    yield f"data: {word} \n\n"
                    await asyncio.sleep(0.03)

            yield "data: [DONE]\n\n"

            # Save conversation
            try:
                db.add(Conversation(user_id=user_id, session_id=session_id, role="user", content=body.message))
                db.add(Conversation(user_id=user_id, session_id=session_id, role="assistant", content=full_response.strip()))
                db.commit()
            except Exception:
                pass

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/providers")
async def list_providers(user_id: int = Depends(get_current_user)):
    """List all LLM providers and their status."""
    try:
        from services.llm_router import get_llm_router
        llm_router = get_llm_router()
        providers = llm_router.get_providers()
        return {"status": "success", "data": providers}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/providers/stats")
async def provider_stats(user_id: int = Depends(get_current_user)):
    """Get LLM router usage statistics."""
    try:
        from services.llm_router import get_llm_router
        llm_router = get_llm_router()
        stats = llm_router.get_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/provider/test")
async def test_provider(
    body: ProviderTestRequest,
    user_id: int = Depends(get_current_user),
):
    """Send a test message to a specific provider."""
    try:
        from services.llm_router import get_llm_router
        llm_router = get_llm_router()
        start = time.time()
        result = await llm_router.route(
            messages=[{"role": "user", "content": "Hello, respond with one word."}],
            preferred_provider=body.provider,
        )
        elapsed = time.time() - start
        return {
            "status": "success",
            "data": {
                "success": True,
                "response_time": round(elapsed, 2),
                "text": result["text"],
                "provider": result.get("provider"),
                "model": result.get("model"),
            },
        }
    except Exception as e:
        return {
            "status": "success",
            "data": {"success": False, "error": str(e)},
        }


@router.put("/provider/priority")
async def update_priorities(
    body: PriorityUpdate,
    user_id: int = Depends(get_current_user),
):
    """Update provider priority order."""
    try:
        from services.llm_router import get_llm_router
        llm_router = get_llm_router()
        llm_router.set_priorities({p.name: p.priority for p in body.priorities})
        return {"status": "success", "data": {"message": "Priorities updated"}}
    except Exception as e:
        return {"status": "error", "message": str(e)}
