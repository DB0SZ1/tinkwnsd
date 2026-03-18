"""
Automation SaaS — FastAPI entry point.

Endpoints:
  GET  /health              — Health check
  GET  /posts               — List published posts
  GET  /leads               — List logged leads
  POST /topics              — Add a new topic
  PUT  /topics/{id}/toggle  — Activate / deactivate a topic
  POST /publish/now         — Manually trigger a publish cycle

All endpoints (except /health) require X-API-Key header.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.models import Base, Lead, Post, Topic, ImageLibrary
from db.session import SessionLocal, engine, get_db
from modules.content_generator import generate_content
from modules.linkedin_publisher import publish_to_linkedin
from modules.x_publisher import publish_to_x
from scheduler import create_scheduler
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Ensure upload dir exists
os.makedirs("uploads", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True) # Symlink or duplicate route for static serving

templates = Jinja2Templates(directory="templates")

# ── Scheduler lifecycle ──────────────────────────────────────────────────

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on startup, shut down on exit."""
    global _scheduler

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    _scheduler = create_scheduler()
    _scheduler.start()
    logger.info("Scheduler started")

    yield

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


app = FastAPI(
    title="Automation SaaS",
    description="Fully automated social media marketing system",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ── Auth dependency ──────────────────────────────────────────────────────

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate the admin API key from request headers."""
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

async def get_current_user(request: Request):
    """Check session cookie for UI access."""
    session_token = request.cookies.get("session_token")
    if not session_token or session_token != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# ── Pydantic schemas ────────────────────────────────────────────────────

class TopicCreate(BaseModel):
    topic: str
    platform: str = "both"
    flavor: str = "random"
    personality: str = "random"

class TopicResponse(BaseModel):
    id: str
    topic: str
    platform: str
    tone: str
    active: bool

    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: str
    platform: str
    content: str
    post_id: Optional[str] = None
    published_at: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class LeadResponse(BaseModel):
    id: str
    name: Optional[str] = None
    profile_url: Optional[str] = None
    platform: str
    post_id: str
    action: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class PublishRequest(BaseModel):
    platform: str = "both"  # "x" | "linkedin" | "both"

# ── Frontend Routes ──────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
async def login_submit(password: str = Form(...)):
    if password == settings.ADMIN_API_KEY:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="session_token", value=settings.ADMIN_API_KEY, httponly=True)
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
        return RedirectResponse(url="/login")
        
    topics = db.query(Topic).filter(Topic.active == True).all()
    recent_posts = db.query(Post).order_by(Post.id.desc()).limit(10).all()
    images = db.query(ImageLibrary).order_by(ImageLibrary.id.desc()).all()
    
    stats = {
        "li_queue": db.query(Post).filter(Post.status == "pending", Post.platform == "linkedin").count(),
        "x_queue": db.query(Post).filter(Post.status == "pending", Post.platform == "x").count(),
        "total_topics": len(topics),
        "total_images": len(images),
        "leads": db.query(Lead).count()
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "topics": topics,
        "recent_posts": recent_posts,
        "images": images,
        "stats": stats
    })

# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/images")
async def upload_image(
    file: UploadFile = File(...),
    tag: str = Form(...),
    db: Session = Depends(get_db),
    _ = Depends(get_current_user)
):
    import shutil
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join("uploads", filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Also copy to static/uploads for UI serving
    file_path_ui = os.path.join("static/uploads", filename)
    shutil.copyfile(file_path, file_path_ui)
        
    img = ImageLibrary(filename=filename, tag=tag)
    db.add(img)
    db.commit()
    return {"status": "ok", "filename": filename}

@app.post("/api/topics")
async def create_topic_ui(body: TopicCreate, db: Session = Depends(get_db), _ = Depends(get_current_user)):
    topic = Topic(
        topic=body.topic,
        platform=body.platform,
        flavor=body.flavor,
        personality=body.personality,
        active=True
    )
    db.add(topic)
    db.commit()
    return {"status": "ok"}


class SettingsUpdate(BaseModel):
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    x_api_key: Optional[str] = None
    x_api_secret: Optional[str] = None
    x_access_token: Optional[str] = None
    x_access_token_secret: Optional[str] = None
    x_username: Optional[str] = None
    x_email: Optional[str] = None
    x_password: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    linkedin_urn: Optional[str] = None
    database_url: Optional[str] = None
    admin_api_key: Optional[str] = None
    timezone: Optional[str] = None

@app.post("/api/settings")
async def update_settings(body: SettingsUpdate, _ = Depends(get_current_user)):
    """Update settings inside the .env file."""
    import re
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    if not os.path.exists(env_path):
        return {"status": "error", "message": ".env file not found"}

    with open(env_path, "r") as f:
        content = f.read()

    fields_map = {
        "OPENROUTER_API_KEY": body.openrouter_api_key,
        "OPENROUTER_MODEL": body.openrouter_model,
        "X_API_KEY": body.x_api_key,
        "X_API_SECRET": body.x_api_secret,
        "X_ACCESS_TOKEN": body.x_access_token,
        "X_ACCESS_TOKEN_SECRET": body.x_access_token_secret,
        "X_USERNAME": body.x_username,
        "X_EMAIL": body.x_email,
        "X_PASSWORD": body.x_password,
        "LINKEDIN_ACCESS_TOKEN": body.linkedin_access_token,
        "LINKEDIN_PERSON_ID": body.linkedin_urn,
        "DATABASE_URL": body.database_url,
        "ADMIN_API_KEY": body.admin_api_key,
        "TIMEZONE": body.timezone,
    }

    for key, val in fields_map.items():
        if val and not val.startswith("***"):
            if key == "LINKEDIN_PERSON_ID" and ":" in val:
                val = val.split(":")[-1]
            
            content = re.sub(rf'{key}=.*', f'{key}={val}', content)

    with open(env_path, "w") as f:
        f.write(content)

    return {"status": "ok"}

@app.post("/api/jobs/{platform}/toggle")
async def toggle_job(platform: str, _ = Depends(get_current_user)):
    """Pause or resume a publisher job."""
    global _scheduler
    if not _scheduler:
        return {"status": "error", "message": "Scheduler not running"}
        
    job_id = f"generate_and_publish_{platform}"
    job = _scheduler.get_job(job_id)
    
    if not job:
        return {"status": "error", "message": "Job not found"}
        
    if job.next_run_time is None:
        job.resume()
        return {"status": "resumed"}
    else:
        job.pause()
        return {"status": "paused"}

@app.get("/posts", response_model=list[PostResponse])
async def list_posts(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
    limit: int = Query(50, ge=1, le=200),
):
    """List published posts, most recent first."""
    posts = (
        db.query(Post)
        .order_by(Post.published_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [
        PostResponse(
            id=str(p.id),
            platform=p.platform,
            content=p.content,
            post_id=p.post_id,
            published_at=p.published_at.isoformat() if p.published_at else None,
            status=p.status,
        )
        for p in posts
    ]


@app.get("/leads", response_model=list[LeadResponse])
async def list_leads(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
    limit: int = Query(50, ge=1, le=200),
):
    """List all logged leads, most recent first."""
    leads = (
        db.query(Lead)
        .order_by(Lead.created_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [
        LeadResponse(
            id=str(l.id),
            name=l.name,
            profile_url=l.profile_url,
            platform=l.platform,
            post_id=str(l.post_id),
            action=l.action,
            created_at=l.created_at.isoformat() if l.created_at else None,
        )
        for l in leads
    ]


@app.post("/topics", response_model=TopicResponse)
async def create_topic(
    body: TopicCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Add a new topic for content generation."""
    topic = Topic(
        topic=body.topic,
        platform=body.platform,
        tone=body.tone,
        active=True,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)

    logger.info("Created topic: %s (%s/%s)", topic.topic, topic.platform, topic.tone)

    return TopicResponse(
        id=str(topic.id),
        topic=topic.topic,
        platform=topic.platform,
        tone=topic.tone,
        active=topic.active,
    )


@app.put("/topics/{topic_id}/toggle", response_model=TopicResponse)
async def toggle_topic(
    topic_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Activate or deactivate a topic."""
    topic = db.query(Topic).filter(Topic.id == uuid.UUID(topic_id)).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic.active = not topic.active
    db.commit()
    db.refresh(topic)

    logger.info("Toggled topic %s → active=%s", topic.id, topic.active)

    return TopicResponse(
        id=str(topic.id),
        topic=topic.topic,
        platform=topic.platform,
        tone=topic.tone,
        active=topic.active,
    )


@app.post("/publish/now")
async def publish_now(
    body: PublishRequest = PublishRequest(),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Manually trigger a publish cycle (admin)."""
    results = {}

    if body.platform in ("x", "both"):
        topics = (
            db.query(Topic)
            .filter(Topic.active.is_(True), Topic.platform.in_(["x", "both"]))
            .all()
        )
        if topics:
            import random
            topic = random.choice(topics)
            try:
                text = await generate_content(topic.topic, platform="x", tone=topic.tone)
                post = await publish_to_x(text, db)
                results["x"] = {"status": "published", "post_id": str(post.id) if post else None}
            except Exception as exc:
                results["x"] = {"status": "failed", "error": str(exc)}
        else:
            results["x"] = {"status": "skipped", "reason": "no active topics"}

    if body.platform in ("linkedin", "both"):
        topics = (
            db.query(Topic)
            .filter(Topic.active.is_(True), Topic.platform.in_(["linkedin", "both"]))
            .all()
        )
        if topics:
            import random
            topic = random.choice(topics)
            try:
                text = await generate_content(topic.topic, platform="linkedin", tone=topic.tone)
                post = await publish_to_linkedin(text, db)
                results["linkedin"] = {"status": "published", "post_id": str(post.id) if post else None}
            except Exception as exc:
                results["linkedin"] = {"status": "failed", "error": str(exc)}
        else:
            results["linkedin"] = {"status": "skipped", "reason": "no active topics"}

    return {"results": results}
