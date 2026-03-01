import os
import httpx
import telebot
import threading
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load any local .env variables
load_dotenv('backend/.env')

# ------------- CONFIGURATION -------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8539049303:AAHsrlThxDkbZM-olIYmfzeCrbY3eqSDCJo")
JEXI_BASE_URL = "https://jexi-flax.vercel.app/api/v1"

# Basic in-memory stores mapping Chat ID
user_tokens = {}
admin_users = {}
user_backend_ids = {} # {chat_id: user_id}
last_seen_msg_ids = {} # {chat_id: {friend_id: last_id}}
last_seen_note_ids = {} # {chat_id: last_id}
user_modes = {}  # Keeps track of whether user is talking to "ai" or a specific friend {"type": "ai", "friend_id": None, "friend_name": None}

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Deduplication: Track suggestions already sent to admins this session ---
processed_suggestion_ids = set()

# --- Local AI Chat History Cache (in-memory fallback for fast response) ---
# Format: {chat_id: [{"role": "user"|"ai", "text": "...", "time": "HH:MM"}]}
local_chat_cache: dict = {}
MAX_LOCAL_CACHE = 50  # Keep last 50 messages per user locally

def get_session_id(chat_id):
    """Returns a stable session ID tied to the Telegram user. 
    Using 'tg_<chat_id>' ensures the AI backend always finds the SAME conversation history."""
    return f"tg_{chat_id}"

def add_to_local_cache(chat_id, role, text):
    """Add a message to the local in-memory chat cache."""
    if chat_id not in local_chat_cache:
        local_chat_cache[chat_id] = []
    now_ist = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%H:%M")
    local_chat_cache[chat_id].append({"role": role, "text": text, "time": now_ist})
    # Trim to max size
    if len(local_chat_cache[chat_id]) > MAX_LOCAL_CACHE:
        local_chat_cache[chat_id] = local_chat_cache[chat_id][-MAX_LOCAL_CACHE:]

def fetch_ai_history_from_cloud(token, session_id, limit=10):
    """Fetch old AI conversation history from the JEXI backend (Supabase)."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(
            f"{JEXI_BASE_URL}/ai/history",
            params={"session_id": session_id, "limit": limit},
            headers=headers, timeout=10.0
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data
    except Exception:
        pass
    return []


def get_jexi_token(chat_id):
    """Retrieve the API token for the specific user/chat session."""
    return user_tokens.get(chat_id)

def get_user_mode(chat_id):
    return user_modes.get(chat_id, {"type": "ai", "friend_id": None, "friend_name": None})

def set_user_mode(chat_id, mode_type, f_id=None, f_name=None):
    user_modes[chat_id] = {"type": mode_type, "friend_id": f_id, "friend_name": f_name}

# --- Core API Calls ---

def ask_jexi_ai(message_text, chat_id, token):
    """Send user text to JEXI AI API with persistent session memory."""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        # Use stable session ID so AI backend always uses the SAME history
        session_id = get_session_id(chat_id)
        payload = {"message": message_text, "session_id": session_id}

        response = httpx.post(f"{JEXI_BASE_URL}/ai/chat", json=payload, headers=headers, timeout=45.0)

        if response.status_code == 401:
            if chat_id in user_tokens: del user_tokens[chat_id]
            return "⏳ Your secure session expired. Please send your `/login <username> <password>` command again."

        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            reply_text = data["data"]["text"]
            # Save to local cache so /myhistory works even if cloud is slow
            add_to_local_cache(chat_id, "user", message_text)
            add_to_local_cache(chat_id, "ai", reply_text)
            return reply_text
        return f"Brain connection error: {data.get('message', 'Unknown Error')}"
    except httpx.TimeoutException:
        return "I'm thinking too hard! (The request timed out)"
    except Exception as e:
        return f"Oops! I dropped a wire. ({str(e)})"


def send_to_friend(message_text, friend_id, token):
    """Send user text to a real friend via the social api."""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"content": message_text, "attachment_url": None}
        response = httpx.post(f"{JEXI_BASE_URL}/social/messages/{friend_id}", json=payload, headers=headers, timeout=10.0)
        
        if response.status_code == 401:
            return None, "⏳ Your secure session expired. Please log in again."
            
        response.raise_for_status()
        # Message sent! Now fetch chat history.
        history_resp = httpx.get(f"{JEXI_BASE_URL}/social/messages/{friend_id}", headers=headers, timeout=10.0)
        if history_resp.status_code == 200:
             history = history_resp.json()
             return history, None
        return [], None
    except Exception as e:
        return None, f"Could not send msg to friend. {str(e)}"

# ------------- BOT HANDLERS -------------

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 **Welcome to JEXI Life OS Bot!**\n\n"
        "Your personal AI-powered Life Assistant.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📋 **Getting Started:**\n"
        "`/login username password` — Log in to JEXI\n"
        "`/register username password` — Create a new account\n"
        "`/logout` — Log out securely\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💬 *Features:*\n"
        "`/ai` — Talk to JEXI AI\n"
        "`/myhistory` — View your last 10 AI messages 🧠\n"
        "`/friends` — Chat with friends\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "👑 **Admin Only:**\n"
        "`/admin_users` — List all users\n"
        "`/create_user user pass` — Create a user account\n"
        "`/suggestions` — View AI-refined suggestions\n\n"
        "🌐 _jexi-flax.vercel.app_"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")


@bot.message_handler(commands=['logout'])
def logout_user(message):
    chat_id = message.chat.id
    if chat_id in user_tokens:
        del user_tokens[chat_id]
        bot.reply_to(message, "✅ Logged out securely. You will need to log in again.")
    else:
        bot.reply_to(message, "You are already logged out.")

@bot.message_handler(commands=['login'])
def login_user(message):
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "❌ Invalid format. Please use:\n`/login username password`", parse_mode="Markdown")
        return
        
    _, username, password = parts
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        response = httpx.post(f"{JEXI_BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=10.0)
        
        if response.status_code == 401:
            bot.reply_to(message, "🚫 Incorrect username or password.")
            return
            
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            login_data = data.get("data", {})
            token = login_data.get("token", "")
            user_tokens[chat_id] = token
            user_backend_ids[chat_id] = login_data.get("id")
            admin_users[chat_id] = login_data.get("is_admin", False)
            set_user_mode(chat_id, "ai")

            admin_tag = " 👑 *[Admin]*" if admin_users[chat_id] else ""
            bot.reply_to(message,
                f"✅ *Login Successful!*\n\n"
                f"Welcome back, *{username}*{admin_tag}!\n"
                f"🧠 JEXI AI is ready. I remember our past conversations!\n"
                f"Type anything to continue. Use `/myhistory` to see our last chat.",
                parse_mode="Markdown")

            try: bot.delete_message(chat_id, message.message_id)
            except: pass

            # Greet with last AI message from cloud history
            try:
                session_id = get_session_id(chat_id)
                history = fetch_ai_history_from_cloud(token, session_id, limit=5)
                if history:
                    # Find last AI message
                    ai_msgs = [m for m in reversed(history) if m.get("role") == "assistant"]
                    if ai_msgs:
                        last_reply = ai_msgs[0]["content"][:300]
                        bot.send_message(chat_id,
                            f"💭 *Last time I told you:*\n_{last_reply}..._",
                            parse_mode="Markdown")
            except Exception:
                pass  # Don't fail login if history fetch fails

        else:
            bot.reply_to(message, "❌ Server login failed. Please check your username and password.")
    except Exception as e:
         bot.reply_to(message, f"❌ Cloud server is unreachable right now: {str(e)}")


@bot.message_handler(commands=['register'])
def register_user(message):
    """Allow new users to create a JEXI account or get instructions."""
    parts = message.text.split()
    chat_id = message.chat.id

    if len(parts) != 3:
        bot.reply_to(message,
            "📝 **Create Your JEXI Account**\n\n"
            "Format: `/register YourName YourPassword`\n\n"
            "⚠️ *Choose a strong password (min 6 chars)!*\n"
            "Your message will be auto-deleted for security.",
            parse_mode="Markdown")
        return

    _, username, password = parts

    if len(password) < 6:
        bot.reply_to(message, "❌ Password must be at least 6 characters long.")
        try: bot.delete_message(chat_id, message.message_id)
        except: pass
        return

    bot.send_chat_action(chat_id, 'typing')

    try:
        # Check existing users to see if setup is done
        check_resp = httpx.get(f"{JEXI_BASE_URL}/auth/users", timeout=10.0)
        users_list = check_resp.json().get("data", []) if check_resp.status_code == 200 else []

        if not users_list:
            # No users exist - use setup route
            response = httpx.post(f"{JEXI_BASE_URL}/auth/setup",
                                  json={"username": username, "password": password}, timeout=10.0)
            if response.status_code in [200, 201]:
                data = response.json()
                login_data = data.get("data", {})
                user_tokens[chat_id] = login_data.get("token", "")
                admin_users[chat_id] = login_data.get("is_admin", False)
                set_user_mode(chat_id, "ai")
                bot.reply_to(message,
                    f"✅ **Account Created & Logged In!**\n\nWelcome, *{username}*! 🎉\nType anything to talk to JEXI AI!",
                    parse_mode="Markdown")
            else:
                err = response.json().get("detail", "Unknown error")
                bot.reply_to(message, f"❌ Registration failed: `{err}`", parse_mode="Markdown")
        else:
            # Admin needs to create accounts for friends
            bot.reply_to(message,
                "⚠️ **New Account Needed**\n\n"
                "Ask the JEXI Admin (*@rajfazulhussain2008*) to create an account for you.\n\n"
                "Alternatively, visit the website directly:\n"
                "🌐 https://jexi-flax.vercel.app/",
                parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Server unreachable: {str(e)}")

    # Always delete the register message to protect the password
    try: bot.delete_message(chat_id, message.message_id)
    except: pass



@bot.message_handler(commands=['admin_users'])
def handle_admin_users(message):
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    if not token:
        bot.reply_to(message, "🔒 Please `/login` first.")
        return
        
    if not admin_users.get(chat_id):
        bot.reply_to(message, "⛔ Access Denied. Admin privileges required.")
        return
        
    bot.send_chat_action(chat_id, 'typing')
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{JEXI_BASE_URL}/admin/users", headers=headers, timeout=10.0)
        
        if resp.status_code == 403:
            bot.reply_to(message, "⛔ The server declined your Admin privileges.")
            return
            
        resp.raise_for_status()
        users = resp.json()
        
        reply = "👑 **JEXI User Database**\n\n"
        for u in users:
            role = "Admin" if u.get("is_admin") else "User"
            reply += f"• `{u['username']}` ({role})\n"
            
        bot.reply_to(message, reply, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error fetching history: {e}")

@bot.message_handler(commands=['active_sessions'])
def list_my_sessions(message):
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    if not token: return
    
    bot.send_chat_action(chat_id, 'typing')
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{JEXI_BASE_URL}/auth/sessions", headers=headers, timeout=10.0)
        resp.raise_for_status()
        sessions = resp.json().get("data", [])
        
        if not sessions:
            bot.reply_to(message, "No active sessions found.")
            return
            
        report = "📱 **Active Login Sessions**\n\n"
        for s in sessions:
            device = s.get('user_agent', 'Unknown')[:40] + "..."
            report += f"📍 IP: `{s.get('ip_address')}`\n📱 Device: {device}\n"
            report += f"🗓 Created: {s.get('created_at', '')[:16]}\n"
            report += "---" * 5 + "\n\n"
            
        report += "\n⚠️ If you see an unknown device, type `/logout_all` immediately."
        bot.reply_to(message, report, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['logout_all'])
def force_logout_all(message):
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    if not token: return
    
    bot.reply_to(message, "⏳ Revoking all sessions...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(f"{JEXI_BASE_URL}/auth/logout-all", headers=headers, timeout=10.0)
        resp.raise_for_status()
        
        bot.reply_to(message, "✅ **Security Lockdown Complete.**\n\nAll session tokens have been revoked. Every device (including this bot session) will be logged out on its next action.\n\nPlease `/login` again to start a new secure session.", parse_mode="Markdown")
        
        # Clear local token too
        if chat_id in user_tokens: del user_tokens[chat_id]
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error during lockdown: {e}")

@bot.message_handler(commands=['create_user'])
def handle_admin_create_user(message):
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    if not token:
        bot.reply_to(message, "🔒 Please `/login` first.")
        return
        
    if not admin_users.get(chat_id):
        bot.reply_to(message, "⛔ Access Denied. Admin privileges required.")
        return
        
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "❌ Format: `/create_user new_username base_password`", parse_mode="Markdown")
        return
        
    _, new_user, new_pass = parts
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"username": new_user, "password": new_pass}
        
        resp = httpx.post(f"{JEXI_BASE_URL}/admin/users", json=payload, headers=headers, timeout=10.0)
        
        if resp.status_code == 400:
            bot.reply_to(message, f"❌ User creation failed: `{resp.json().get('detail', 'Username probably exists.')}`", parse_mode="Markdown")
            return
        elif resp.status_code == 403:
            bot.reply_to(message, "⛔ The server declined your Admin privileges.")
            return
            
        resp.raise_for_status()
        
        bot.reply_to(message, f"✅ **User Created Successfully!**\n\n`{new_user}` is now registered and has been automatically added to your Friends list.", parse_mode="Markdown")
        try: bot.delete_message(chat_id, message.message_id)
        except: pass
    except Exception as e:
        bot.reply_to(message, f"❌ API Error: {e}")

@bot.message_handler(commands=['suggestions'])
def handle_view_suggestions(message):
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    if not token:
        bot.reply_to(message, "🔒 Please `/login` first.")
        return
        
    if not admin_users.get(chat_id):
        bot.reply_to(message, "⛔ Access Denied.")
        return
        
    bot.send_chat_action(chat_id, 'typing')
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{JEXI_BASE_URL}/admin/suggestions", headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        
        processed = data.get("processed", [])
        
        if not processed:
            bot.reply_to(message, "📭 No AI-refined suggestions found yet. Wait for a friend to submit one!")
            return
            
        report = "📜 **AI-Refined Suggestions History**\n\n"
        for p in processed:
            # Value is stored as "Suggestion: [text] \n\n Plan: [text]"
            val = p.get("value", "")
            report += f"{val}\n"
            report += "---" * 5 + "\n\n"
            
        # Split message if it's too long for Telegram
        if len(report) > 4000:
            for x in range(0, len(report), 4000):
                bot.send_message(chat_id, report[x:x+4000], parse_mode="Markdown")
        else:
            bot.reply_to(message, report, parse_mode="Markdown")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['myhistory'])
def show_my_ai_history(message):
    """Show the last 10 AI chat messages for the user."""
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    if not token:
        bot.reply_to(message, "🔒 Please `/login` first.", parse_mode="Markdown")
        return

    bot.send_chat_action(chat_id, 'typing')

    # Try cloud history first
    session_id = get_session_id(chat_id)
    cloud_history = fetch_ai_history_from_cloud(token, session_id, limit=10)

    if cloud_history:
        report = "🧠 *Your JEXI AI Conversation History*\n\n"
        for msg in cloud_history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]
            icon = "👤 You" if role == "user" else "🤖 JEXI"
            # Try to parse timestamp
            raw_ts = msg.get("created_at", "") or msg.get("timestamp", "")
            ts_str = ""
            if raw_ts:
                try:
                    dt_utc = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                    dt_ist = dt_utc + timedelta(hours=5, minutes=30)
                    ts_str = f" _{dt_ist.strftime('%d %b, %H:%M')}_"
                except Exception:
                    pass
            report += f"*{icon}*{ts_str}:\n{content}\n{'—' * 12}\n\n"

        if len(report) > 4000:
            report = report[-4000:]

        bot.reply_to(message, report, parse_mode="Markdown")
        return

    # Fallback to local in-memory cache this session
    local = local_chat_cache.get(chat_id, [])
    if local:
        report = "🧠 *Your AI Chat This Session*\n_(Full cloud history unavailable right now)_\n\n"
        for entry in local[-10:]:
            icon = "👤 You" if entry["role"] == "user" else "🤖 JEXI"
            report += f"*{icon}* [{entry['time']}]:\n{entry['text'][:200]}\n{'—' * 12}\n\n"
        bot.reply_to(message, report, parse_mode="Markdown")
    else:
        bot.reply_to(message, "📭 No AI conversation history found yet.\n\nStart chatting with JEXI AI and it will be stored here!", parse_mode="Markdown")


@bot.message_handler(commands=['ai'])
def switch_to_ai(message):
    chat_id = message.chat.id
    if not get_jexi_token(chat_id):
        bot.reply_to(message, "🔒 Please `/login username pass` first.")
        return


    set_user_mode(chat_id, "ai")
    bot.reply_to(message, "🤖 **Mode switched to AI Assistant.** Any message you send now will go to JEXI.")

@bot.message_handler(commands=['friends'])
def list_friends(message):
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    if not token:
        bot.reply_to(message, "🔒 Please `/login username pass` first.")
        return
        
    bot.send_chat_action(chat_id, 'typing')
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = httpx.get(f"{JEXI_BASE_URL}/social/friends", headers=headers, timeout=10.0)
        
        if resp.status_code == 401:
            bot.reply_to(message, "⏳ Your secure session expired. Please log in again.")
            return
            
        resp.raise_for_status()
        data = resp.json()
        friends = data if isinstance(data, list) else data.get("data", [])
        
        if not friends:
             bot.reply_to(message, "You don't have any friends listed in JEXI right now! Tell an Admin to add some.")
             return
             
        markup = InlineKeyboardMarkup()
        for f in friends:
            # Add an inline button for each friend
            btn = InlineKeyboardButton(f["name"], callback_data=f"chat_{f['id']}_{f['name']}")
            markup.add(btn)
            
        bot.reply_to(message, "👥 **Your JEXI Friends**\n\nTap a friend below to start a direct message with them:", reply_markup=markup, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Could not load friends: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("chat_"))
def handle_friend_chat_selection(call):
    """Triggered when a user clicks a friend's inline button."""
    chat_id = call.message.chat.id
    _, friend_id, friend_name = call.data.split("_", 2)
    
    set_user_mode(chat_id, "friend", friend_id, friend_name)
    bot.answer_callback_query(call.id, f"Switched to chatting with {friend_name}")
    
    # Send a confirmation in chat
    bot.send_message(chat_id, f"💬 **Mode switched to Private Chat with {friend_name}.**\n\nAny message you send now will be delivered directly to their JEXI inbox!\n*(Type `/ai` if you want to switch back to the robot)*", parse_mode="Markdown")

@bot.message_handler(commands=['chat_history'])
def fetch_history(message):
    """Fetch the last few messages of the currently active friend."""
    chat_id = message.chat.id
    token = get_jexi_token(chat_id)
    mode = get_user_mode(chat_id)
    
    if not token: return
    if mode["type"] != "friend":
        bot.reply_to(message, "You are not currently chatting with a friend. Type `/friends` to pick someone.")
        return
        
    bot.send_chat_action(chat_id, 'typing')
    friend_id = mode["friend_id"]
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{JEXI_BASE_URL}/social/messages/{friend_id}", headers=headers, timeout=10.0)
        resp.raise_for_status()
        history = resp.json()
        
        if not history:
             bot.reply_to(message, f"No previous messages with {mode['friend_name']}.")
             return
             
        # Format the last 5 messages
        history_str = f"📜 **Last Messages with {mode['friend_name']}**\n\n"
        for h in history[-5:]:
             raw_ts = h.get('timestamp', '')
             ts_str = "??:??"
             if raw_ts:
                 try:
                     # Parse UTC timestamp and convert to IST (+5:30)
                     dt_utc = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                     dt_ist = dt_utc + timedelta(hours=5, minutes=30)
                     ts_str = dt_ist.strftime("%H:%M")
                 except:
                     ts_str = raw_ts[11:16] if len(raw_ts) > 16 else "??:??"
                     
             sender = "Them" if str(h.get('sender_id')) == str(friend_id) else "You"
             history_str += f"*{sender}* [{ts_str}]: {h.get('content', '')}\n"
             if h.get('attachment_url'):
                 history_str += f"📎 [Attachment]({h['attachment_url']})\n"
                 
        bot.reply_to(message, history_str, parse_mode="Markdown")
    except Exception as e:
         pass


@bot.message_handler(func=lambda message: True)
def process_text(message):
    chat_id = message.chat.id
    user_text = message.text
    token = get_jexi_token(chat_id)
    
    if not token:
        bot.reply_to(message, "🔒 This is a private assistant.\n\nPlease authenticate first by typing:\n`/login username password`", parse_mode="Markdown")
        return
    
    bot.send_chat_action(chat_id, 'typing')
    
    # Check what mode we are in
    mode = get_user_mode(chat_id)
    
    if mode["type"] == "ai":
        # Chatting with Jexi AI
        response_text = ask_jexi_ai(user_text, chat_id, token)
        bot.reply_to(message, response_text)
        
    elif mode["type"] == "friend":
        # Chatting with a human friend
        friend_id = mode["friend_id"]
        friend_name = mode["friend_name"]
        
        history, error = send_to_friend(user_text, friend_id, token)
        
        if error:
            bot.reply_to(message, error)
        else:
             # Just briefly acknowledge it sent to make it feel responsive
             bot.reply_to(message, f"✅ Sent to {friend_name}!")
             
             # Instead of pinging them their own message back, if we wanted to show new replies 
             # we would need websockets. For now, since it's REST, they can type /chat_history
             # to fetch recent messages.

def poll_suggestions():
    """Poll for new unprocessed suggestions and notify admins. Uses in-memory dedup."""
    global processed_suggestion_ids
    while True:
        time.sleep(60)  # Poll every 60 seconds (was 15 — too aggressive)
        admin_chat_id = None
        for cid, is_admin in list(admin_users.items()):
            if is_admin:
                admin_chat_id = cid
                break

        if not admin_chat_id:
            continue

        token = get_jexi_token(admin_chat_id)
        if not token:
            continue

        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = httpx.get(f"{JEXI_BASE_URL}/admin/suggestions", headers=headers, timeout=10.0)
            if resp.status_code != 200:
                continue

            data = resp.json()
            suggestions = data.get("unprocessed", [])

            for sugg in suggestions:
                sugg_id = sugg.get("id")

                # ✅ DEDUP FIX: Skip if we already processed this suggestion this session
                if sugg_id in processed_suggestion_ids:
                    continue

                # Mark as seen IMMEDIATELY before any async work to prevent double-send
                processed_suggestion_ids.add(sugg_id)

                # AI refine the suggestion
                prompt = f"A user suggested this for my platform: '{sugg['value']}'. As an expert AI, evaluate this suggestion and give me a clear, step-by-step action plan on what I should do."
                ai_payload = {"message": prompt, "session_id": f"admin_suggestion_{sugg_id}"}

                try:
                    ai_resp = httpx.post(f"{JEXI_BASE_URL}/ai/chat", json=ai_payload, headers=headers, timeout=45.0)
                    if ai_resp.status_code != 200:
                        continue

                    plan = ai_resp.json()["data"]["text"]
                    msg = (
                        f"💡 **New Suggestion Alert!**\n\n"
                        f"**Suggestion:** _{sugg['value']}_\n\n"
                        f"🤖 **AI Action Plan:**\n{plan}"
                    )

                    # Notify all admins (only ONCE per suggestion)
                    for cid, is_admin in list(admin_users.items()):
                        if is_admin:
                            bot.send_message(cid, msg, parse_mode="Markdown")

                    # Save to memory_facts for /suggestions command
                    try:
                        from supabase_rest import sb_insert
                        sb_insert("memory_facts", {
                            "user_id": user_backend_ids.get(admin_chat_id, 1),
                            "key": f"ai_plan_{sugg_id}",
                            "value": f"💡 **Suggestion:** {sugg['value']}\n\n🤖 **AI Plan:** {plan}",
                            "auto_extracted": False
                        })
                    except Exception as save_err:
                        print(f"[BOT] Could not save suggestion plan: {save_err}")

                    # Delete the raw suggestion from DB so it won't appear in 'unprocessed' again
                    try:
                        del_resp = httpx.delete(
                            f"{JEXI_BASE_URL}/admin/suggestions/{sugg_id}",
                            headers=headers, timeout=10.0
                        )
                        if del_resp.status_code not in [200, 204]:
                            print(f"[BOT] Warning: Could not delete suggestion {sugg_id}: {del_resp.status_code}")
                    except Exception as del_err:
                        print(f"[BOT] Delete error for suggestion {sugg_id}: {del_err}")

                except Exception as ai_err:
                    print(f"[BOT] AI refinement error for suggestion {sugg_id}: {ai_err}")
                    # Remove from processed set so it retries next cycle
                    processed_suggestion_ids.discard(sugg_id)

        except Exception as poll_err:
            print(f"[BOT] poll_suggestions error: {poll_err}")

def poll_chat_messages():
    """Poll for new incoming messages from friends for all logged-in users."""
    while True:
        time.sleep(5) # Poll chat every 5 seconds
        
        # Iterate over all users currently logged in
        for chat_id in list(user_tokens.keys()):
            token = user_tokens.get(chat_id)
            mode = user_modes.get(chat_id, {"type": "ai"})
            
            # Only poll if they are currently in friend-chat mode
            if mode.get("type") == "friend" and mode.get("friend_id"):
                friend_id = mode["friend_id"]
                friend_name = mode["friend_name"]
                
                try:
                    headers = {"Authorization": f"Bearer {token}"}
                    resp = httpx.get(f"{JEXI_BASE_URL}/social/messages/{friend_id}", headers=headers, timeout=10.0)
                    
                    if resp.status_code == 200:
                        messages = resp.json()
                        if not messages: continue
                        
                        # Filter for messages from the friend (not from the user)
                        incoming = [m for m in messages if str(m.get("sender_id")) == str(friend_id)]
                        if not incoming: continue
                        
                        # Track last seen ID to only show NEW messages
                        if chat_id not in last_seen_msg_ids: last_seen_msg_ids[chat_id] = {}
                        last_id = last_seen_msg_ids[chat_id].get(friend_id, 0)
                        
                        new_msgs = [m for m in incoming if m.get("id", 0) > last_id]
                        
                        for m in new_msgs:
                            msg_text = m.get("content", "")
                            # Convert UTC to IST
                            raw_ts = m.get('timestamp', '')
                            ts_str = ""
                            if raw_ts:
                                try:
                                    dt_utc = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                                    dt_ist = dt_utc + timedelta(hours=5, minutes=30)
                                    ts_str = f" [{dt_ist.strftime('%H:%M')}]"
                                except: pass
                                
                            alert = f"💬 **{friend_name}**{ts_str}:\n{msg_text}"
                            if m.get("attachment_url"):
                                alert += f"\n📎 [Attachment]({m['attachment_url']})"
                                
                            bot.send_message(chat_id, alert, parse_mode="Markdown")
                            
                            # Update water-mark
                            last_seen_msg_ids[chat_id][friend_id] = max(last_id, m.get("id", 0))
                            
                        # If first time loading history, just set the watermark to latest
                        if last_id == 0 and incoming:
                            last_seen_msg_ids[chat_id][friend_id] = max([m.get("id", 0) for m in incoming])
                            
                except Exception:
                    pass

def poll_notifications():
    """Poll for unread system notifications (Security alerts, etc) for all logged-in users."""
    while True:
        time.sleep(10) # Poll and alert every 10 seconds
        for chat_id in list(user_tokens.keys()):
            token = user_tokens.get(chat_id)
            if not token: continue
            
            try:
                headers = {"Authorization": f"Bearer {token}"}
                resp = httpx.get(f"{JEXI_BASE_URL}/notifications", headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    notes = data.get("data", [])
                    
                    last_id = last_seen_note_ids.get(chat_id, 0)
                    new_notes = [n for n in notes if n.get("id", 0) > last_id]
                    
                    for n in new_notes:
                        icon = "🔔"
                        if n.get("type") == "warning": icon = "⚠️ **SECURITY ALERT**"
                        
                        msg = f"{icon}\n\n**{n.get('title', 'Notification')}**\n{n.get('message', '')}"
                        bot.send_message(chat_id, msg, parse_mode="Markdown")
                        
                        # Mark as read in backend
                        httpx.post(f"{JEXI_BASE_URL}/notifications/{n['id']}/read", headers=headers)
                        
                        last_id = max(last_id, n.get("id", 0))
                    
                    last_seen_note_ids[chat_id] = last_id
                    
                    # If first time, just set the watermark
                    if last_id == 0 and notes:
                        last_seen_note_ids[chat_id] = max([n.get("id", 0) for n in notes])
                        
            except Exception:
                pass

if __name__ == "__main__":
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("ERROR: Please update TELEGRAM_BOT_TOKEN in this script or your .env file!")
    else:
        print("JEXI Secure Social Telegram Bot is starting up and listening...")
        # Start background pollers
        threading.Thread(target=poll_suggestions, daemon=True).start()
        threading.Thread(target=poll_chat_messages, daemon=True).start()
        threading.Thread(target=poll_notifications, daemon=True).start()
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
