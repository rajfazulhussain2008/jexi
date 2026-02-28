import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys (comma-separated for rotation) ---
GROQ_API_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]
GEMINI_API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
COHERE_API_KEYS = [k.strip() for k in os.getenv("COHERE_API_KEYS", "").split(",") if k.strip()]
OPENROUTER_API_KEYS = [k.strip() for k in os.getenv("OPENROUTER_API_KEYS", "").split(",") if k.strip()]
HF_API_KEYS = [k.strip() for k in os.getenv("HF_API_KEYS", "").split(",") if k.strip()]
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_KEYS = [k.strip() for k in os.getenv("CLOUDFLARE_API_KEYS", "").split(",") if k.strip()]
NVIDIA_API_KEYS = [k.strip() for k in os.getenv("NVIDIA_API_KEYS", "").split(",") if k.strip()]
SAMBANOVA_API_KEYS = [k.strip() for k in os.getenv("SAMBANOVA_API_KEYS", "").split(",") if k.strip()]
CEREBRAS_API_KEYS = [k.strip() for k in os.getenv("CEREBRAS_API_KEYS", "").split(",") if k.strip()]

# --- JWT Configuration ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 720  # 30 days

# --- Database ---
# Default to local SQLite, but prefer environment variable (for Vercel/Supabase)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/jexi.db")

# Fix for common SQLAlchemy issues with postgres:// vs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- Assistant ---
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "JEXI")
USER_NAME = os.getenv("USER_NAME", "User")

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
