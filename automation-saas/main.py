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
from sqlalchemy.orm import Session

from db.models import Base, Lead, Post, Topic, ImageLibrary
from db.session import SessionLocal, engine, get_db
from core.security import get_current_user
from routers.api import api_router
from scheduler import create_scheduler
from utils.config import settings
from utils.logger import get_logger

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
