"""
bot_routes.py — Telegram Bot Webhook Handler for Vercel.
Switches from local polling to cloud webhook so the bot runs 24/7.
Webhook URL: https://jexi-flax.vercel.app/api/v1/bot/webhook
"""
import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/bot", tags=["Telegram Bot"])

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8539049303:AAHsrlThxDkbZM-olIYmfzeCrbY3eqSDCJo")
JEXI_BASE_URL = "https://jexi-flax.vercel.app/api/v1"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── In-memory session store (resets on cold start — acceptable for serverless) ──
# For full persistence, this can be stored in Supabase.
user_tokens: dict = {}
admin_users: dict = {}
user_modes: dict = {}
user_backend_ids: dict = {}

# ── Helpers ──────────────────────────────────────────────────────────────────

def tg_send(chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Send a message to a Telegram chat."""
    with httpx.Client(timeout=10) as client:
        client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        })

def tg_delete(chat_id: int, message_id: int):
    """Delete a message from Telegram chat."""
    try:
        with httpx.Client(timeout=5) as client:
            client.post(f"{TELEGRAM_API}/deleteMessage", json={
                "chat_id": chat_id,
                "message_id": message_id
            })
    except Exception:
        pass

def tg_action(chat_id: int, action: str = "typing"):
    """Show typing indicator."""
    try:
        with httpx.Client(timeout=5) as client:
            client.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": action})
    except Exception:
        pass

def get_user_mode(chat_id):
    return user_modes.get(chat_id, {"type": "ai", "friend_id": None, "friend_name": None})

def set_user_mode(chat_id, mode_type, f_id=None, f_name=None):
    user_modes[chat_id] = {"type": mode_type, "friend_id": f_id, "friend_name": f_name}

def jexi_login(username: str, password: str):
    """Authenticate with JEXI backend."""
    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{JEXI_BASE_URL}/auth/login", json={"username": username, "password": password})
        return resp.status_code, resp.json()

def jexi_ai_chat(message: str, session_id: str, token: str):
    """Send a message to JEXI AI."""
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        with httpx.Client(timeout=45) as client:
            resp = client.post(f"{JEXI_BASE_URL}/ai/chat", json={
                "message": message,
                "session_id": session_id
            }, headers=headers)
            if resp.status_code == 401:
                return None, "expired"
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return data["data"]["text"], None
            return None, "ai_error"
    except httpx.TimeoutException:
        return "⏱️ The AI is thinking too hard! Try again in a moment.", None
    except Exception as e:
        return None, str(e)

def jexi_get_friends(token: str):
    """Get friends list."""
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{JEXI_BASE_URL}/social/friends", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        return []

def jexi_send_message(to_id: str, content: str, token: str):
    """Send a message to a friend via JEXI."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=10) as client:
        resp = client.post(f"{JEXI_BASE_URL}/social/messages/{to_id}",
                           json={"content": content, "attachment_url": None}, headers=headers)
        return resp.status_code == 200

# ── Message Command Handlers ─────────────────────────────────────────────────

def handle_start(chat_id: int):
    tg_send(chat_id, (
        "🤖 *Welcome to JEXI Life OS Bot!* 🧠\n\n"
        "Your AI-powered personal Life Assistant.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📋 *Getting Started:*\n"
        "`/login username password` — Log in\n"
        "`/register username password` — Create account\n"
        "`/logout` — Log out securely\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💬 *Features:*\n"
        "`/ai` — Talk to JEXI AI\n"
        "`/friends` — Chat with friends\n"
        "`/chat_history` — View recent messages\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "👑 *Admin Only:*\n"
        "`/admin_users` — List all users\n"
        "`/create_user user pass` — Create a user\n"
        "`/suggestions` — View AI-refined suggestions\n\n"
        "🌐 _jexi-flax.vercel.app_"
    ))

def handle_login(chat_id: int, parts: list, message_id: int):
    if len(parts) != 3:
        tg_send(chat_id, "❌ Format: `/login username password`")
        return
    _, username, password = parts
    tg_action(chat_id)
    status_code, data = jexi_login(username, password)
    if status_code == 401:
        tg_send(chat_id, "🚫 Incorrect username or password.")
        return
    if status_code != 200:
        tg_send(chat_id, f"❌ Server error ({status_code}). Try again.")
        return
    if data.get("status") == "success":
        login_data = data.get("data", {})
        user_tokens[chat_id] = login_data.get("token", "")
        user_backend_ids[chat_id] = login_data.get("id")
        admin_users[chat_id] = login_data.get("is_admin", False)
        set_user_mode(chat_id, "ai")
        admin_tag = " 👑 *[Admin]*" if admin_users[chat_id] else ""
        tg_send(chat_id, f"✅ *Login Successful!*\n\nWelcome, *{username}*{admin_tag}!\nYou are now speaking to *JEXI AI*.\nType `/friends` to chat with people!")
        tg_delete(chat_id, message_id)
    else:
        tg_send(chat_id, "❌ Login failed. Check your credentials.")

def handle_register(chat_id: int, parts: list, message_id: int):
    if len(parts) != 3:
        tg_send(chat_id, (
            "📝 *Create Your JEXI Account*\n\n"
            "Format: `/register YourName YourPassword`\n\n"
            "⚠️ *Choose a strong password (min 6 chars)!*\n"
            "Your message will be auto-deleted for security."
        ))
        return
    _, username, password = parts
    if len(password) < 6:
        tg_send(chat_id, "❌ Password must be at least 6 characters.")
        tg_delete(chat_id, message_id)
        return
    tg_action(chat_id)
    try:
        with httpx.Client(timeout=15) as client:
            check = client.get(f"{JEXI_BASE_URL}/auth/users", timeout=10)
            users_list = check.json().get("data", []) if check.status_code == 200 else []

        if not users_list:
            with httpx.Client(timeout=15) as client:
                resp = client.post(f"{JEXI_BASE_URL}/auth/setup", json={"username": username, "password": password})
            if resp.status_code in [200, 201]:
                login_data = resp.json().get("data", {})
                user_tokens[chat_id] = login_data.get("token", "")
                admin_users[chat_id] = login_data.get("is_admin", False)
                set_user_mode(chat_id, "ai")
                tg_send(chat_id, f"✅ *Account Created & Logged In!*\n\nWelcome, *{username}*! 🎉\nType anything to start talking to JEXI AI!")
            else:
                err = resp.json().get("detail", "Unknown error")
                tg_send(chat_id, f"❌ Registration failed: `{err}`")
        else:
            tg_send(chat_id, (
                "⚠️ *Registration is Admin-Controlled*\n\n"
                "Ask the JEXI Admin to create an account for you.\n"
                "They use: `/create_user yourname yourpass`\n\n"
                "🌐 https://jexi-flax.vercel.app/"
            ))
    except Exception as e:
        tg_send(chat_id, f"❌ Server unreachable: {str(e)}")
    tg_delete(chat_id, message_id)

def handle_logout(chat_id: int):
    if chat_id in user_tokens:
        del user_tokens[chat_id]
        user_modes.pop(chat_id, None)
        admin_users.pop(chat_id, None)
        tg_send(chat_id, "✅ Logged out securely. Use `/login` to log back in.")
    else:
        tg_send(chat_id, "You are not logged in.")

def handle_friends(chat_id: int):
    token = user_tokens.get(chat_id)
    if not token:
        tg_send(chat_id, "🔒 Please `/login` first.")
        return
    tg_action(chat_id)
    friends = jexi_get_friends(token)
    if not friends:
        tg_send(chat_id, "You have no friends in JEXI yet. Ask an Admin to add some!")
        return
    # Build inline keyboard buttons via sendMessage
    keyboard = {
        "inline_keyboard": [[{"text": f["name"], "callback_data": f"chat_{f['id']}_{f['name']}"}] for f in friends]
    }
    with httpx.Client(timeout=10) as client:
        client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": "👥 *Your JEXI Friends*\n\nTap a name to start chatting:",
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        })

def handle_callback(chat_id: int, callback_id: str, data: str):
    """Handle inline keyboard button presses."""
    with httpx.Client(timeout=5) as client:
        client.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": callback_id})
    if data.startswith("chat_"):
        parts = data.split("_", 2)
        if len(parts) == 3:
            _, friend_id, friend_name = parts
            set_user_mode(chat_id, "friend", friend_id, friend_name)
            tg_send(chat_id, (
                f"💬 *Chatting with {friend_name}*\n\n"
                f"Any message you send now goes directly to their JEXI inbox!\n"
                f"Type `/ai` to switch back to the AI assistant."
            ))

def handle_admin_users(chat_id: int):
    token = user_tokens.get(chat_id)
    if not token:
        tg_send(chat_id, "🔒 Please `/login` first.")
        return
    if not admin_users.get(chat_id):
        tg_send(chat_id, "⛔ Admin only command.")
        return
    tg_action(chat_id)
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{JEXI_BASE_URL}/admin/users", headers={"Authorization": f"Bearer {token}"})
        users = resp.json()
        reply = "👑 *JEXI User Database*\n\n"
        for u in users:
            role = "Admin 👑" if u.get("is_admin") else "User"
            reply += f"• `{u['username']}` — {role}\n"
        tg_send(chat_id, reply)
    except Exception as e:
        tg_send(chat_id, f"❌ Error: {e}")

def handle_create_user(chat_id: int, parts: list, message_id: int):
    token = user_tokens.get(chat_id)
    if not token or not admin_users.get(chat_id):
        tg_send(chat_id, "⛔ Admin only command.")
        tg_delete(chat_id, message_id)
        return
    if len(parts) != 3:
        tg_send(chat_id, "Format: `/create_user username password`")
        return
    _, new_user, new_pass = parts
    tg_action(chat_id)
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        with httpx.Client(timeout=10) as client:
            resp = client.post(f"{JEXI_BASE_URL}/admin/users",
                               json={"username": new_user, "password": new_pass},
                               headers=headers)
        if resp.status_code in [200, 201]:
            tg_send(chat_id, f"✅ User `{new_user}` created successfully!")
        else:
            err = resp.json().get("detail", "Unknown error")
            tg_send(chat_id, f"❌ Failed: `{err}`")
    except Exception as e:
        tg_send(chat_id, f"❌ Error: {e}")
    tg_delete(chat_id, message_id)

def handle_text(chat_id: int, text: str):
    token = user_tokens.get(chat_id)
    if not token:
        tg_send(chat_id, (
            "🔒 *Authentication Required*\n\n"
            "Please log in to use JEXI:\n"
            "`/login username password`\n\n"
            "New here? `/register username password`"
        ))
        return
    tg_action(chat_id)
    mode = get_user_mode(chat_id)
    if mode["type"] == "ai":
        reply, error = jexi_ai_chat(text, str(chat_id), token)
        if error == "expired":
            user_tokens.pop(chat_id, None)
            tg_send(chat_id, "⏳ Session expired. Please `/login` again.")
        elif reply:
            tg_send(chat_id, reply)
        else:
            tg_send(chat_id, f"❌ AI error: {error}")
    elif mode["type"] == "friend":
        success = jexi_send_message(mode["friend_id"], text, token)
        if success:
            tg_send(chat_id, f"✅ Sent to *{mode['friend_name']}*!")
        else:
            tg_send(chat_id, "❌ Could not send message. Try again.")

# ── Webhook Endpoint ──────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Main Telegram webhook handler — receives all updates from Telegram."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": True})

    # Handle callback queries (inline button presses)
    if "callback_query" in body:
        cq = body["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        callback_id = cq["id"]
        data = cq.get("data", "")
        handle_callback(chat_id, callback_id, data)
        return JSONResponse({"ok": True})

    message = body.get("message", {})
    if not message:
        return JSONResponse({"ok": True})

    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    message_id = message.get("message_id", 0)

    if not text:
        return JSONResponse({"ok": True})

    parts = text.split()
    cmd = parts[0].lower().split("@")[0]  # Handle /cmd@BotName format

    if cmd in ["/start", "/help"]:
        handle_start(chat_id)
    elif cmd == "/login":
        handle_login(chat_id, parts, message_id)
    elif cmd == "/register":
        handle_register(chat_id, parts, message_id)
    elif cmd == "/logout":
        handle_logout(chat_id)
    elif cmd == "/ai":
        set_user_mode(chat_id, "ai")
        tg_send(chat_id, "🤖 *Switched to AI Mode.* Type anything to chat with JEXI!")
    elif cmd == "/friends":
        handle_friends(chat_id)
    elif cmd == "/admin_users":
        handle_admin_users(chat_id)
    elif cmd == "/create_user":
        handle_create_user(chat_id, parts, message_id)
    elif cmd == "/suggestions":
        token = user_tokens.get(chat_id)
        if not token or not admin_users.get(chat_id):
            tg_send(chat_id, "⛔ Admin only.")
        else:
            tg_send(chat_id, "📜 Loading suggestions...")
            try:
                with httpx.Client(timeout=15) as client:
                    resp = client.get(f"{JEXI_BASE_URL}/admin/suggestions",
                                      headers={"Authorization": f"Bearer {token}"})
                processed = resp.json().get("processed", []) if resp.status_code == 200 else []
                if not processed:
                    tg_send(chat_id, "📭 No suggestions yet.")
                else:
                    report = "📜 *AI-Refined Suggestions*\n\n"
                    for p in processed[-5:]:
                        report += f"{p.get('value', '')}\n{'—'*10}\n\n"
                    tg_send(chat_id, report[:4000])
            except Exception as e:
                tg_send(chat_id, f"❌ Error: {e}")
    else:
        handle_text(chat_id, text)

    return JSONResponse({"ok": True})

# ── Bot Management API ────────────────────────────────────────────────────────

@router.post("/set-webhook")
async def set_webhook(request: Request):
    """Register the webhook URL with Telegram. Call this once after deploying."""
    body = await request.json()
    webhook_url = body.get("url", f"https://jexi-flax.vercel.app/api/v1/bot/webhook")
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(f"{TELEGRAM_API}/setWebhook", json={"url": webhook_url, "drop_pending_updates": True})
        data = resp.json()
        return {"status": "success" if data.get("ok") else "error", "telegram_response": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def bot_status():
    """Get the current bot and webhook status."""
    try:
        with httpx.Client(timeout=10) as client:
            me_resp = client.get(f"{TELEGRAM_API}/getMe")
            wh_resp = client.get(f"{TELEGRAM_API}/getWebhookInfo")
        me = me_resp.json().get("result", {})
        wh = wh_resp.json().get("result", {})
        return {
            "status": "success",
            "data": {
                "bot_name": me.get("first_name"),
                "bot_username": me.get("username"),
                "webhook_url": wh.get("url", "Not set"),
                "webhook_active": bool(wh.get("url")),
                "pending_updates": wh.get("pending_update_count", 0),
                "last_error": wh.get("last_error_message", None),
                "active_sessions": len(user_tokens),
                "bot_link": f"https://t.me/{me.get('username', '')}"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/webhook")
async def delete_webhook():
    """Remove the webhook (reverts to polling mode)."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(f"{TELEGRAM_API}/deleteWebhook")
        return {"status": "success", "telegram_response": resp.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
