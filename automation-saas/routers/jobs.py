import random
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.models import Topic
from db.session import get_db
from core.security import get_current_user, verify_api_key
from schemas.requests import PublishRequest
from modules.content_generator import generate_content
from modules.linkedin_publisher import publish_to_linkedin
from modules.x_publisher import publish_to_x
from utils.image_utils import select_best_image, download_remote_image
import os

router = APIRouter(tags=["Jobs"])

@router.post("/jobs/{platform}/toggle")
async def toggle_job(platform: str, _: bool = Depends(get_current_user)):
    """Pause or resume a publisher job."""
    import main  # Need to access scheduler from main
    if not main._scheduler:
        return {"status": "error", "message": "Scheduler not running"}
        
    job_id = f"generate_and_publish_{platform}"
    job = main._scheduler.get_job(job_id)
    
    if not job:
        return {"status": "error", "message": "Job not found"}
        
    if job.next_run_time is None:
        job.resume()
        return {"status": "resumed"}
    else:
        job.pause()
        return {"status": "paused"}

@router.post("/publish/now")
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
            topic = random.choice(topics)
            try:
                text = await generate_content(topic.topic, platform="x", personality=topic.personality or "random")
                
                # Image matching
                img_path = None
                img_obj = await select_best_image(text, db)
                if img_obj:
                    if img_obj.cloudinary_url:
                        img_path = await download_remote_image(img_obj.cloudinary_url)
                    elif img_obj.filename:
                        local_path = os.path.join("uploads", img_obj.filename)
                        if os.path.exists(local_path):
                            img_path = local_path
                
                post = await publish_to_x(text, db, image_path=img_path)
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
            topic = random.choice(topics)
            try:
                text = await generate_content(topic.topic, platform="linkedin", personality=topic.personality or "random")
                
                # Image matching
                img_path = None
                img_obj = await select_best_image(text, db)
                if img_obj:
                    if img_obj.cloudinary_url:
                        img_path = await download_remote_image(img_obj.cloudinary_url)
                    elif img_obj.filename:
                        local_path = os.path.join("uploads", img_obj.filename)
                        if os.path.exists(local_path):
                            img_path = local_path
                            
                post = await publish_to_linkedin(text, db, image_path=img_path)
                results["linkedin"] = {"status": "published", "post_id": str(post.id) if post else None}
            except Exception as exc:
                results["linkedin"] = {"status": "failed", "error": str(exc)}
            except Exception as exc:
                results["linkedin"] = {"status": "failed", "error": str(exc)}
        else:
            results["linkedin"] = {"status": "skipped", "reason": "no active topics"}

    return {"results": results}

@router.post("/engine/scout")
async def scout_trends_now(db: Session = Depends(get_db)):
    """Trigger the scouting engine manually and return discovered topics."""
    try:
        from modules.scout import get_trending_context
        from db.models import Topic
        import re
        
        context = await get_trending_context()
        new_topics = []
        
        # 1. Extract X Trends
        x_prefix = "CURRENT X TRENDS (Nigeria/Regional):"
        if x_prefix in context:
            try:
                # Find the part after the prefix but before the next double newline
                parts = context.split(x_prefix)[1].split("\n\n")[0].strip()
                trends = [t.strip() for t in parts.split(',')]
                for t_text in trends[:5]:
                    if not t_text: continue
                    existing = db.query(Topic).filter(Topic.topic == t_text).first()
                    if not existing:
                        new_t = Topic(topic=t_text, platform="x", is_automated=True, flavor="hottake", personality="trend-analyst")
                        db.add(new_t)
                        new_topics.append(t_text)
            except Exception as ex:
                logger.error(f"Failed to parse X trends from context: {ex}")
                    
        # 2. Extract Tech News
        news_prefix = "LATEST TECH/AI NEWS:"
        if news_prefix in context:
            try:
                # Find the part after the prefix
                parts = context.split(news_prefix)[1].split("\n\n")[0].strip()
                news_items = [n.strip() for n in parts.split('|')]
                for n_text in news_items[:5]:
                    # Extract just the title part (before the hyphen)
                    title = n_text.split(' - ')[0].strip()
                    if not title: continue
                    existing = db.query(Topic).filter(Topic.topic == title).first()
                    if not existing:
                        new_t = Topic(topic=title, platform="linkedin", is_automated=True, flavor="tips", personality="github-discoverer")
                        db.add(new_t)
                        new_topics.append(title)
            except Exception as ex:
                logger.error(f"Failed to parse Tech news from context: {ex}")
                    
        db.commit()
        return {
            "status": "success", 
            "message": f"Scouted {len(new_topics)} new topics.",
            "new_topics": new_topics,
            "context_preview": context[:500] + "..."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
