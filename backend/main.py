import os
import sys

# Ensure this directory is in the path for Vercel and other runners
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import init_db

# Include active routers
try:
    from routes.auth_routes import router as auth_router
except Exception as e:
    print("Warning: auth_routes not found or failed to load.", e)
    auth_router = None

try:
    from routes.ai_routes import router as ai_router
except Exception as e:
    print("Warning: ai_routes not found or failed to load.", e)
    ai_router = None

try:
    from routes.social_routes import router as social_router
except Exception as e:
    print("Warning: social_routes not found or failed to load.", e)
    social_router = None

try:
    from routes.admin_routes import router as admin_router
except Exception as e:
    print("Warning: admin_routes not found or failed to load.", e)
    admin_router = None

try:
    from routes.notification_routes import router as notification_router
except Exception as e:
    print("Warning: notification_routes not found or failed to load.", e)
    notification_router = None

try:
    from routes.task_routes import router as task_router
except Exception as e:
    print("Warning: task_routes not found.", e)
    task_router = None

try:
    from routes.goal_routes import router as goal_router
except Exception as e:
    print("Warning: goal_routes not found.", e)
    goal_router = None

try:
    from routes.habit_routes import router as habit_router
except Exception as e:
    print("Warning: habit_routes not found.", e)
    habit_router = None

try:
    from routes.journal_routes import router as journal_router
except Exception as e:
    print("Warning: journal_routes not found.", e)
    journal_router = None

try:
    from routes.finance_routes import router as finance_router
except Exception as e:
    print("Warning: finance_routes not found.", e)
    finance_router = None

try:
    from routes.health_routes import router as health_router
except Exception as e:
    print("Warning: health_routes not found.", e)
    health_router = None

# Initialize db configuration
try:
    init_db()
except Exception as e:
    print(f"Database init skipped or failed: {e}")

app = FastAPI(title="JEXI AI Life OS")

@app.get("/api/v1/health-check")
async def health():
    return {"status": "ok", "message": "Backend is alive!"}

@app.get("/api/v1/debug/token")
async def debug_token(request: Request):
    """Debug endpoint — checks if the Authorization header token is valid."""
    from auth import verify_token
    from config import JWT_SECRET
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return {"valid": False, "reason": "No Authorization header found"}
    if not auth_header.startswith("Bearer "):
        return {"valid": False, "reason": "Header does not start with 'Bearer '", "header": auth_header[:50]}
    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)
    if payload is None:
        return {"valid": False, "reason": "Token invalid or expired", "token_preview": token[:30] + "...", "jwt_secret_preview": JWT_SECRET[:10] + "..."}
    return {"valid": True, "user_id": payload.get("user_id"), "username": payload.get("username")}

# Configure CORS for Mobile App Support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your mobile domain/local origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attempt to mount routes if they exist
if auth_router:
    app.include_router(auth_router)
if ai_router:
    app.include_router(ai_router)
if social_router:
    app.include_router(social_router)
if admin_router:
    app.include_router(admin_router)
if notification_router:
    app.include_router(notification_router)
if task_router:
    app.include_router(task_router)
if goal_router:
    app.include_router(goal_router)
if habit_router:
    app.include_router(habit_router)
if journal_router:
    app.include_router(journal_router)
if finance_router:
    app.include_router(finance_router)
if health_router:
    app.include_router(health_router)

# Locate frontend folder
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(frontend_dir):
    # Mount frontend static folders
    css_dir = os.path.join(frontend_dir, "css")
    js_dir = os.path.join(frontend_dir, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

    # Serve manifest.json
    @app.get("/manifest.json")
    async def serve_manifest():
        manifest_path = os.path.join(frontend_dir, "manifest.json")
        if os.path.exists(manifest_path):
            return FileResponse(manifest_path, media_type="application/json")
        return {"error": "Manifest file not found"}

    # Serve sw.js (Service Worker must be served with correct MIME type)
    @app.get("/sw.js")
    async def serve_sw():
        sw_path = os.path.join(frontend_dir, "sw.js")
        if os.path.exists(sw_path):
            return FileResponse(sw_path, media_type="application/javascript")
        return {"error": "Service worker not found"}

    # Serve index.html for SPA rules
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/v1"):
            return {"error": "Endpoint not implemented yet", "detail": "Missing endpoint"}
        
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend not found"}
else:
    @app.get("/")
    async def fallback():
        return {"status": "JEXI Backend is running, but frontend folder not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
