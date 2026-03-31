"""
Automation SaaS — FastAPI entry point.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from db.models import Base, Lead, Post, Topic, ImageLibrary
from db.session import SessionLocal, engine, get_db
from core.security import get_current_user
from routers.api import api_router
from scheduler import create_scheduler
from utils.config import settings
from utils.logger import get_logger
from modules.x_publisher import _get_client, check_x_auth, publish_to_x
from modules.linkedin_publisher import check_li_auth, publish_to_linkedin

logger = get_logger(__name__)

os.makedirs("uploads", exist_ok=True)
if settings.HTML.lower() == "true":
    os.makedirs("static/uploads", exist_ok=True)

from utils.cloud_sync import restore_db_from_cloudinary

# ── Scheduler lifecycle ──────────────────────────────────────────────────
_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on startup, shut down on exit."""
    global _scheduler
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")
    
    # Hydrate the SQLite database from Cloudinary before accepting requests
    restore_db_from_cloudinary()
    
    _scheduler = create_scheduler()
    _scheduler.start()
    logger.info("Scheduler started")
    yield
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

app = FastAPI(
    title="Automation SaaS API",
    description="Fully automated social media marketing system API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handlers for APIs ──────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=422,
            content={"success": False, "error": "Validation Error", "details": exc.errors()}
        )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail}
        )
    # Let FastAPI handle default HTML/JSON HTTP exceptions for frontend
    from fastapi.exception_handlers import http_exception_handler as default_http_handler
    return await default_http_handler(request, exc)


# ── API Routes ──────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Conditional Frontend Routes ──────────────────────────────────────────
if settings.HTML.lower() == "true":
    templates = Jinja2Templates(directory="templates")
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: str = None):
        return templates.TemplateResponse(request, "login.html", {"error": error})

    @app.post("/login")
    async def login_submit(password: str = Form(...)):
        if password.strip() == settings.ADMIN_API_KEY.strip():
            response = RedirectResponse(url="/?success=1", status_code=303)
            response.set_cookie(
                key="session_token", 
                value=settings.ADMIN_API_KEY, 
                httponly=True,
                samesite="lax",
                path="/"
            )
            return response
        return RedirectResponse(url="/login?error=Invalid Credentials", status_code=302)

    @app.get("/logout")
    async def logout():
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("session_token")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request, db: Session = Depends(get_db)):
        try:
            await get_current_user(request)
        except HTTPException:
            return RedirectResponse(url="/login", status_code=302)
            
        user_topics = db.query(Topic).filter(Topic.active == True, Topic.is_automated == False).all()
        automated_topics = db.query(Topic).filter(Topic.active == True, Topic.is_automated == True).all()
        recent_posts = db.query(Post).order_by(Post.id.desc()).all() # Show all recent history
        images = db.query(ImageLibrary).order_by(ImageLibrary.id.desc()).all()
        
        stats = {
            "li_queue": db.query(Post).filter(Post.status == "pending", Post.platform == "linkedin").count(),
            "x_queue": db.query(Post).filter(Post.status == "pending", Post.platform == "x").count(),
            "total_topics": len(user_topics),
            "total_trends": len(automated_topics),
            "total_images": len(images),
            "leads": db.query(Lead).count()
        }
        
        return templates.TemplateResponse(request, "index.html", {
            "topics": user_topics,
            "automated_topics": automated_topics,
            "recent_posts": recent_posts,
            "images": images,
            "stats": stats
        })
# API: AI PERSONA MANAGEMENT
@app.get("/api/v1/persona")
async def get_persona_files():
    persona_dir = os.path.join(os.path.dirname(__file__), "persona")
    files = ["persona.md", "how_to_write.md", "memory.md"]
    data = {}
    for f_name in files:
        f_path = os.path.join(persona_dir, f_name)
        if os.path.exists(f_path):
            with open(f_path, "r", encoding="utf-8") as f:
                data[f_name] = f.read()
        else:
            data[f_name] = f"# {f_name.upper()}\n(File not found)"
    return data

@app.post("/api/v1/persona")
async def update_persona_files(data: dict):
    persona_dir = os.path.join(os.path.dirname(__file__), "persona")
    for f_name, content in data.items():
        if f_name in ["persona.md", "how_to_write.md", "memory.md"]:
            f_path = os.path.join(persona_dir, f_name)
            with open(f_path, "w", encoding="utf-8") as f:
                f.write(content)
    return {"status": "success"}

# API: X DIAGNOSTICS
@app.get("/api/v1/debug/x-auth")
async def debug_x_auth():
    try:
        # This will trigger the logger.info diagnostic block in _get_client
        client = _get_client()
        return {"status": "success", "message": "X Authentication Successful!"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# API: SYSTEM HEALTH & LOGS
@app.get("/api/v1/system/health")
async def get_system_health():
    # Check Database
    db_status = "healthy"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check X
    x_health = check_x_auth()
    
    # Check LinkedIn
    li_health = await check_li_auth()
    
    # Check OpenRouter (Basic check)
    or_health = "healthy" if settings.OPENROUTER_API_KEY else "missing_key"
    
    return {
        "database": db_status,
        "x": x_health,
        "linkedin": li_health,
        "openrouter": or_health,
        "timestamp": os.popen("date /t").read().strip() + " " + os.popen("time /t").read().strip()
    }

@app.get("/api/v1/system/logs")
async def get_system_logs():
    log_path = os.path.join(os.path.dirname(__file__), "logs", "app.log")
    if not os.path.exists(log_path):
        return {"logs": "Log file not found yet. Generate some activity!"}
    
    try:
        # Use PowerShell tail equivalent or just read last N lines
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return {"logs": "".join(lines[-100:])} # Last 100 lines
    except Exception as e:
        return {"logs": f"Error reading logs: {e}"}

@app.post("/api/v1/system/manual-post/{platform}")
async def trigger_manual_post(platform: str):
    from db.session import SessionLocal
    db = SessionLocal()
    try:
        # Find oldest active topic for this platform
        topic = db.query(Topic).filter(
            Topic.active == True,
            (Topic.platform == platform) | (Topic.platform == "both")
        ).order_by(Topic.id).first()
        
        if not topic:
            return {"status": "failed", "message": f"No active topics found for {platform}"}
        
        # Generate and Publish
        from modules.content_generator import generate_content
        content, memory_log = await generate_content(topic.topic, platform, topic.flavor, topic.personality)
        
        if platform == "x":
            result = await publish_to_x(content, db)
        else:
            result = await publish_to_linkedin(content, db)
            
        if result:
            # Update memory
            from utils.memory_utils import update_memory_log
            update_memory_log(memory_log)
            return {"status": "success", "message": f"Successfully pushed manual post to {platform}"}
        else:
            return {"status": "failed", "message": f"Publisher failed for {platform}. Check logs."}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
