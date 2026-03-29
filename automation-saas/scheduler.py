"""
APScheduler setup — registers all recurring jobs.

Jobs:
  1. generate_and_publish_x       — daily 08:00 UTC (09:00 WAT)
  2. generate_and_publish_linkedin — daily 09:00 UTC (10:00 WAT)
  3. track_engagement              — daily 15:00 UTC (16:00 WAT)
  4. log_leads                     — daily 16:00 UTC (17:00 WAT)

All jobs are wrapped in try/except so failures never crash the scheduler.
"""

from __future__ import annotations

import asyncio
import random

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db.models import Topic, ImageLibrary, PostMetric, Lead
from utils.twilio_client import send_whatsapp_message
from utils.config import settings
from db.session import SessionLocal
from modules.content_generator import generate_content
from modules.engagement_tracker import track_all_recent
from modules.lead_logger import log_leads_for_recent
from modules.linkedin_publisher import publish_to_linkedin
from modules.x_publisher import publish_to_x
from modules.scout import get_trending_context
from utils.image_utils import select_best_image
from utils.logger import get_logger
from utils.notifications import send_push_notification_sync
from utils.cloud_sync import backup_db_to_cloudinary, keep_alive_ping

logger = get_logger(__name__)

def _get_matched_image_path(db: SessionLocal, text: str, platform: str) -> str | None:
    """Try to find the best matching image using AI descriptions, fallback to random."""
    import os
    try:
        filename = _run_async(select_best_image(text, db))
        if filename:
            path = os.path.join("uploads", filename)
            if os.path.exists(path):
                logger.info(f"Using matched image for {platform}: {filename}")
                return path
    except Exception as e:
        logger.error(f"Image matching failed: {e}")

    # Fallback to legacy random picker
    return _get_random_image_path(db, platform)

def _get_random_image_path(db: SessionLocal, platform: str) -> str | None:
    """Fetch a random image matching the platform rules (Legacy Fallback)."""
    import os
    valid_tags_x = ['personal', 'meme', 'quote', 'infographic']
    valid_tags_li = ['headshot', 'infographic', 'quote', 'ui', 'dashboard']
    tags = valid_tags_x if platform == "x" else valid_tags_li

    images = db.query(ImageLibrary).filter(
        ImageLibrary.tag.in_(tags),
        ImageLibrary.platform_bias.in_([platform, "both"])
    ).all()

    if not images:
        return None

    img = random.choice(images)
    path = os.path.join("uploads", img.filename)
    if os.path.exists(path):
        return path
    return None

def _run_async(coro):
    """Run an async coroutine from a sync scheduler job."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ── Job 1: Generate and publish to X ─────────────────────────────────────

def generate_and_publish_x() -> None:
    """Pick a random active topic or scout trends, generate X content, publish."""
    try:
        db = SessionLocal()
        
        topic_text = "General Tech Tips"
        context = None
        
        if settings.TOPICS_ENGINE == "automatic":
            context = _run_async(get_trending_context())
            # For X, we pick one of the trends as the primary topic
            if "X TRENDS" in context:
                # Extract first trend
                import re
                trends = re.search(r"CURRENT X TRENDS.*?: (.*?)\b", context)
                if trends:
                    topics_list = trends.group(1).split(',')
                    topic_text = topics_list[0].strip()
                    # Persist as automated topic if not exists
                    existing = db.query(Topic).filter(Topic.topic == topic_text).first()
                    if not existing:
                        new_t = Topic(
                            topic=topic_text, 
                            platform="x", 
                            is_automated=True,
                            flavor="hottake", 
                            personality="trend-analyst"
                        )
                        db.add(new_t)
                        db.commit()
            logger.info(f"Automatic mode: Scouting X trends. Topic: {topic_text}")
        else:
            topics = db.query(Topic).filter(Topic.active.is_(True), Topic.platform.in_(["x", "both"])).all()
            if not topics:
                logger.warning("No active X topics found — skipping publish")
                db.close()
                return
            t_obj = random.choice(topics)
            topic_text = t_obj.topic
            logger.info("Selected topic for X (Manual): %s", topic_text)

        text = _run_async(generate_content(
            topic_text, 
            platform="x", 
            context=context
        ))
        
        img_path = _get_matched_image_path(db, text, "x")
        _run_async(publish_to_x(text, db, image_path=img_path))

        db.close()
        send_push_notification_sync(
            title="🐦 X Post Published!",
            message=f"Topic: {topic_text[:50]}...",
            priority=3,
            tags="bird,robot"
        )
    except Exception as exc:
        logger.error("generate_and_publish_x failed: %s", exc, exc_info=True)
        send_push_notification_sync("❌ X Publish Failed", str(exc), priority=4, tags="warning")

# ── Job 2: Generate and publish to LinkedIn ──────────────────────────────

def generate_and_publish_linkedin() -> None:
    """Pick a random active topic or scout trends, generate LinkedIn content, publish."""
    try:
        db = SessionLocal()
        
        topic_text = "Software Engineering Excellence"
        context = None
        
        if settings.TOPICS_ENGINE == "automatic":
            context = _run_async(get_trending_context())
            # Save a representative topic from news if possible
            if "TECH NEWS" in context:
                import re
                news = re.search(r"TOP TECH NEWS.*?: (.*?)\b", context)
                if news:
                    topic_text = news.group(1).split('|')[0].strip()
                    existing = db.query(Topic).filter(Topic.topic == topic_text).first()
                    if not existing:
                        new_t = Topic(
                            topic=topic_text, 
                            platform="linkedin", 
                            is_automated=True,
                            flavor="tips", 
                            personality="github-discoverer"
                        )
                        db.add(new_t)
                        db.commit()
            logger.info("Automatic mode: Scouting news for LinkedIn.")
        else:
            topics = db.query(Topic).filter(Topic.active.is_(True), Topic.platform.in_(["linkedin", "both"])).all()
            if not topics:
                logger.warning("No active LinkedIn topics found — skipping publish")
                db.close()
                return
            t_obj = random.choice(topics)
            topic_text = t_obj.topic
            logger.info("Selected topic for LinkedIn (Manual): %s", topic_text)

        # Rotate personalities for LinkedIn 5x slots
        personalities = ["github-discoverer", "10x-shipper", "work-advertiser", "trend-analyst", "lead-magnet"]
        personality = random.choice(personalities)

        text = _run_async(generate_content(
            topic_text, 
            platform="linkedin", 
            personality=personality,
            context=context
        ))
        
        img_path = _get_matched_image_path(db, text, "linkedin")
        _run_async(publish_to_linkedin(text, db, image_path=img_path))

        db.close()
        send_push_notification_sync(
            title="🔵 LinkedIn Post Published!",
            message=f"Topic: {topic_text[:50]}...\nPersona: {personality}",
            priority=3,
            tags="blue_book,robot"
        )
    except Exception as exc:
        logger.error("generate_and_publish_linkedin failed: %s", exc, exc_info=True)
        send_push_notification_sync("❌ LinkedIn Publish Failed", str(exc), priority=4, tags="warning")


# ── Job 3+: Support Jobs ────────────────────────────────────────────────

def track_engagement() -> None:
    """Run engagement tracking for posts from the last 7 days."""
    try:
        db = SessionLocal()
        _run_async(track_all_recent(db, lookback_days=7))
        db.close()
    except Exception as exc:
        logger.error("track_engagement failed: %s", exc, exc_info=True)

def log_leads() -> None:
    """Run lead logging for posts from the last 7 days."""
    try:
        db = SessionLocal()
        _run_async(log_leads_for_recent(db, lookback_days=7))
        db.close()
    except Exception as exc:
        logger.error("log_leads failed: %s", exc, exc_info=True)

def send_whatsapp_analytics() -> None:
    """Gather metrics and send a daily summary to the user's WhatsApp."""
    if not settings.USER_WHATSAPP_NUMBER or not settings.TWILIO_ACCOUNT_SID:
        return
    try:
        db = SessionLocal()
        metrics = db.query(PostMetric).all()
        leads = db.query(Lead).count()
        likes = sum(m.likes for m in metrics)
        comments = sum(m.comments for m in metrics)
        db.close()
        reply = f"📊 *Daily Analytics Summary*\n👍 Total Likes: {likes}\n💬 Total Comments: {comments}\n🎯 Total Leads: {leads}\n\n_Sent automatically by your SAAS Bot_"
        send_whatsapp_message(settings.USER_WHATSAPP_NUMBER, reply)
    except Exception as exc:
        logger.error("send_whatsapp_analytics failed: %s", exc, exc_info=True)


# ── Scheduler factory ───────────────────────────────────────────────────

def create_scheduler() -> BackgroundScheduler:
    """Create and configure the BackgroundScheduler with all jobs."""
    scheduler = BackgroundScheduler(timezone="UTC")

    # X publishing — 2 times daily (08:00 and 16:00 WAT -> 07:00 and 15:00 UTC)
    for hour in [7, 15]:
        scheduler.add_job(
            generate_and_publish_x,
            trigger=CronTrigger(hour=hour, minute=0, jitter=600),
            id=f"x_publish_{hour}",
            name=f"X Publish @ {hour}:00 UTC",
            replace_existing=True,
        )

    # LinkedIn publishing — 5 times daily (07:00, 10:00, 13:00, 16:00, 19:00 UTC)
    for hour in [7, 10, 13, 16, 19]:
        scheduler.add_job(
            generate_and_publish_linkedin,
            trigger=CronTrigger(hour=hour, minute=0, jitter=600),
            id=f"li_publish_{hour}",
            name=f"LinkedIn Publish @ {hour}:00 UTC",
            replace_existing=True,
        )

    # Supporting Jobs
    scheduler.add_job(track_engagement, trigger=CronTrigger(hour=15, minute=0), id="track_engagement")
    scheduler.add_job(log_leads, trigger=CronTrigger(hour=16, minute=0), id="log_leads")
    scheduler.add_job(backup_db_to_cloudinary, trigger="interval", hours=3, id="db_backup")
    scheduler.add_job(send_whatsapp_analytics, trigger=CronTrigger(hour=17, minute=30), id="wa_analytics")
    scheduler.add_job(keep_alive_ping, trigger="interval", minutes=10, id="keep_alive_ping")

    logger.info("Scheduler configured with 12 active job slots")
    return scheduler
