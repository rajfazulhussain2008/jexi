import os
import httpx
import telebot
import threading
import time
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
user_modes = {}  # Keeps track of whether user is talking to "ai" or a specific friend {"type": "ai", "friend_id": None, "friend_name": None}

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def get_jexi_token(chat_id):
    """Retrieve the API token for the specific user/chat session."""
    return user_tokens.get(chat_id)

def get_user_mode(chat_id):
    return user_modes.get(chat_id, {"type": "ai", "friend_id": None, "friend_name": None})

def set_user_mode(chat_id, mode_type, f_id=None, f_name=None):
    user_modes[chat_id] = {"type": mode_type, "friend_id": f_id, "friend_name": f_name}

# --- Core API Calls ---

def ask_jexi_ai(message_text, chat_id, token):
    """Send user text to JEXI AI API."""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"message": message_text, "session_id": str(chat_id)}
        
        response = httpx.post(f"{JEXI_BASE_URL}/ai/chat", json=payload, headers=headers, timeout=45.0)
        
        if response.status_code == 401:
            if chat_id in user_tokens: del user_tokens[chat_id]
            return "⏳ Your secure session expired. Please send your `/login <username> <password>` command again."
            
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            return data["data"]["text"]
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
        "🤖 **Welcome to the JEXI Multi-Assist Bot!**\n\n"
        "This bot requires a Jexi dashboard account.\n\n"
        "**Comamnds:**\n"
        "`/login username pass` - Log in securely\n"
        "`/logout` - Log out securely\n"
        "`/ai` - Talk to your Jexi AI Assistant (default)\n"
        "`/friends` - List your friends & start chatting with them\n\n"
        "*(Admins Only)*\n"
        "`/admin_users` - List all registered Jexi users\n"
        "`/create_user user pass` - Make a new user & friend them automatically\n"
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
            user_tokens[chat_id] = data["data"]["token"]
            
            # Grant admin super-powers in Telegram
            admin_users[chat_id] = data["data"].get("is_admin", False)
            
            set_user_mode(chat_id, "ai") # Default to AI mode
            bot.reply_to(message, f"✅ **Login Successful!**\n\nWelcome back, *{username}*! You are now speaking to **JEXI AI**.\nType `/friends` to chat with real people!", parse_mode="Markdown")
            
            try: bot.delete_message(chat_id, message.message_id)
            except: pass
        else:
            bot.reply_to(message, "❌ Server login failed.")
    except Exception as e:
         bot.reply_to(message, f"❌ Cloud server is unreachable right now: {str(e)}")

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
        bot.reply_to(message, f"❌ Failed to fetch users: {e}")

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
             ts = h.get('timestamp', '')[11:16] # extract HH:MM
             sender = "Them" if str(h.get('sender_id')) == str(friend_id) else "You"
             history_str += f"*{sender}* [{ts}]: {h.get('content', '')}\n"
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
    while True:
        time.sleep(15)  # Poll every 15 seconds
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
            if resp.status_code == 200:
                suggestions = resp.json()
                for sugg in suggestions:
                    # AI refine the suggestion
                    prompt = f"A user suggested this for my platform: '{sugg['value']}'. As an expert AI, evaluate this suggestion and give me a clear, step-by-step action plan on what I should do."
                    
                    ai_payload = {"message": prompt, "session_id": f"admin_suggestion_{sugg['id']}"}
                    ai_resp = httpx.post(f"{JEXI_BASE_URL}/ai/chat", json=ai_payload, headers=headers, timeout=45.0)
                    
                    if ai_resp.status_code == 200:
                        plan = ai_resp.json()["data"]["text"]
                        
                        msg = f"💡 **New Application Suggestion from User!**\n\n"
                        msg += f"**Suggestion:** _{sugg['value']}_\n\n"
                        msg += f"🤖 **AI Analysis & Action Plan:**\n{plan}"
                        
                        # Notify all admins
                        for cid, is_admin in list(admin_users.items()):
                            if is_admin:
                                bot.send_message(cid, msg, parse_mode="Markdown")
                        
                        # Delete the suggestion so it's not processed again
                        httpx.delete(f"{JEXI_BASE_URL}/admin/suggestions/{sugg['id']}", headers=headers, timeout=10.0)
        except Exception as e:
            pass

if __name__ == "__main__":
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("ERROR: Please update TELEGRAM_BOT_TOKEN in this script or your .env file!")
    else:
        print("JEXI Secure Social Telegram Bot is starting up and listening...")
        # Start suggestion background poller
        threading.Thread(target=poll_suggestions, daemon=True).start()
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
