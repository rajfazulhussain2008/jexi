import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
from fastapi import FastAPI
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

# Initialize db configuration
init_db()

app = FastAPI(title="JEXI AI Life OS")

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
