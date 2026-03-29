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
        x_match = re.search(r"CURRENT X TRENDS.*?: (.*?)\b", context)
        if x_match:
            trends = x_match.group(1).split(',')
            for t_text in trends[:5]: # Take top 5
                t_text = t_text.strip()
                if not t_text: continue
                existing = db.query(Topic).filter(Topic.topic == t_text).first()
                if not existing:
                    new_t = Topic(topic=t_text, platform="x", is_automated=True, flavor="hottake", personality="trend-analyst")
                    db.add(new_t)
                    new_topics.append(t_text)
                    
        # 2. Extract Tech News
        news_match = re.search(r"LATEST TECH/AI NEWS: (.*?)\b", context)
        if news_match:
            news = news_match.group(1).split('|')
            for n_text in news[:3]:
                n_text = n_text.strip().split('-')[0].strip() # Take just the title
                if not n_text: continue
                existing = db.query(Topic).filter(Topic.topic == n_text).first()
                if not existing:
                    new_t = Topic(topic=n_text, platform="linkedin", is_automated=True, flavor="tips", personality="github-discoverer")
                    db.add(new_t)
                    new_topics.append(n_text)
                    
        db.commit()
        return {
            "status": "success", 
            "message": f"Scouted {len(new_topics)} new topics.",
            "new_topics": new_topics,
            "context_preview": context[:500] + "..."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
