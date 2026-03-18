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

from db.models import Topic, ImageLibrary
from db.session import SessionLocal
from modules.content_generator import generate_content
from modules.engagement_tracker import track_all_recent
from modules.lead_logger import log_leads_for_recent
from modules.linkedin_publisher import publish_to_linkedin
from modules.x_publisher import publish_to_x
from utils.logger import get_logger
from utils.notifications import send_push_notification_sync

logger = get_logger(__name__)

def _get_random_image_path(db: SessionLocal, platform: str) -> str | None:
    """Fetch a random image matching the platform rules."""
    import os
    valid_tags_x = ['personal', 'meme', 'quote', 'infographic']
    valid_tags_li = ['headshot', 'infographic', 'quote']
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
    """Pick a random active topic, generate X content, publish."""
    try:
        db = SessionLocal()
        topics = db.query(Topic).filter(Topic.active.is_(True), Topic.platform.in_(["x", "both"])).all()

        if not topics:
            logger.warning("No active X topics found — skipping publish")
            db.close()
            return

        topic = random.choice(topics)
        logger.info("Selected topic for X: %s", topic.topic)

        text = _run_async(generate_content(
            topic.topic, 
            platform="x", 
            flavor=topic.flavor, 
            personality=topic.personality
        ))
        
        img_path = _get_random_image_path(db, "x")
        _run_async(publish_to_x(text, db, image_path=img_path))

        db.close()
        send_push_notification_sync(
            title="🐦 X Post Published!",
            message=f"Topic: {topic.topic[:50]}...\nFlavor: {topic.flavor}",
            priority=3,
            tags="bird,robot"
        )
    except Exception as exc:
        logger.error("generate_and_publish_x failed: %s", exc, exc_info=True)
        send_push_notification_sync("❌ X Publish Failed", str(exc), priority=4, tags="warning")

# ── Job 2: Generate and publish to LinkedIn ──────────────────────────────

def generate_and_publish_linkedin() -> None:
    """Pick a random active topic, generate LinkedIn content, publish."""
    try:
        db = SessionLocal()
        topics = db.query(Topic).filter(Topic.active.is_(True), Topic.platform.in_(["linkedin", "both"])).all()

        if not topics:
            logger.warning("No active LinkedIn topics found — skipping publish")
            db.close()
            return

        topic = random.choice(topics)
        logger.info("Selected topic for LinkedIn: %s", topic.topic)

        text = _run_async(generate_content(
            topic.topic, 
            platform="linkedin", 
            flavor=topic.flavor, 
            personality=topic.personality
        ))
        
        img_path = _get_random_image_path(db, "linkedin")
        _run_async(publish_to_linkedin(text, db, image_path=img_path))

        db.close()
        send_push_notification_sync(
            title="🔵 LinkedIn Post Published!",
            message=f"Topic: {topic.topic[:50]}...\nFlavor: {topic.flavor}",
            priority=3,
            tags="blue_book,robot"
        )
    except Exception as exc:
        logger.error("generate_and_publish_linkedin failed: %s", exc, exc_info=True)
        send_push_notification_sync("❌ LinkedIn Publish Failed", str(exc), priority=4, tags="warning")


# ── Job 3: Track engagement ──────────────────────────────────────────────

def track_engagement() -> None:
    """Run engagement tracking for posts from the last 7 days."""
    try:
        db = SessionLocal()
        _run_async(track_all_recent(db, lookback_days=7))
        db.close()
    except Exception as exc:
        logger.error("track_engagement failed: %s", exc, exc_info=True)


# ── Job 4: Log leads ────────────────────────────────────────────────────

def log_leads() -> None:
    """Run lead logging for posts from the last 7 days."""
    try:
        db = SessionLocal()
        _run_async(log_leads_for_recent(db, lookback_days=7))
        db.close()
    except Exception as exc:
        logger.error("log_leads failed: %s", exc, exc_info=True)


# ── Scheduler factory ───────────────────────────────────────────────────

def create_scheduler() -> BackgroundScheduler:
    """Create and configure the BackgroundScheduler with all jobs."""
    scheduler = BackgroundScheduler(timezone="UTC")

    # Job 1 — X publishing at 08:00 UTC (09:00 WAT) ± 15 mins jitter
    scheduler.add_job(
        generate_and_publish_x,
        trigger=CronTrigger(hour=8, minute=0, jitter=900),
        id="generate_and_publish_x",
        name="Generate & Publish to X",
        replace_existing=True,
    )

    # Job 2 — LinkedIn publishing at 09:00 UTC (10:00 WAT) ± 15 mins jitter
    scheduler.add_job(
        generate_and_publish_linkedin,
        trigger=CronTrigger(hour=9, minute=0, jitter=900),
        id="generate_and_publish_linkedin",
        name="Generate & Publish to LinkedIn",
        replace_existing=True,
    )

    # Job 3 — Engagement tracking at 15:00 UTC (16:00 WAT)
    scheduler.add_job(
        track_engagement,
        trigger=CronTrigger(hour=15, minute=0),
        id="track_engagement",
        name="Track Engagement",
        replace_existing=True,
    )

    # Job 4 — Lead logging at 16:00 UTC (17:00 WAT)
    scheduler.add_job(
        log_leads,
        trigger=CronTrigger(hour=16, minute=0),
        id="log_leads",
        name="Log Leads",
        replace_existing=True,
    )

    logger.info("Scheduler configured with 4 jobs")
    return scheduler
