"""
Lead logger — identifies users who engage with published posts and stores
them as potential leads in the DB.

LinkedIn: Fetches likers and commenters via the socialActions API.
X:        Stub — free tier does not expose engagement user data.

Usage:
    await log_leads_for_recent(db_session, lookback_days=7)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from db.models import Lead, Post
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def _linkedin_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


async def _log_linkedin_likes(post: Post, db: Session) -> int:
    """Fetch and store likers for a LinkedIn post. Returns count logged."""
    if not post.post_id:
        return 0

    try:
        url = f"{LINKEDIN_API_BASE}/socialActions/{post.post_id}/likes"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_linkedin_headers())
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        count = 0

        for el in elements:
            actor = el.get("actor", "")
            # Avoid duplicate leads
            existing = (
                db.query(Lead)
                .filter(
                    Lead.profile_url == actor,
                    Lead.post_id == post.id,
                    Lead.action == "like",
                )
                .first()
            )
            if existing:
                continue

            lead = Lead(
                name=actor.split(":")[-1] if actor else "unknown",
                profile_url=f"https://www.linkedin.com/in/{actor.split(':')[-1]}" if actor else "",
                platform="linkedin",
                post_id=post.id,
                action="like",
                created_at=datetime.now(timezone.utc),
            )
            db.add(lead)
            count += 1

        db.commit()
        return count

    except Exception as exc:
        logger.error("Failed to fetch LinkedIn likes for %s: %s", post.post_id, exc)
        return 0


async def _log_linkedin_comments(post: Post, db: Session) -> int:
    """Fetch and store commenters for a LinkedIn post. Returns count logged."""
    if not post.post_id:
        return 0

    try:
        url = f"{LINKEDIN_API_BASE}/socialActions/{post.post_id}/comments"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_linkedin_headers())
            resp.raise_for_status()
            data = resp.json()

        elements = data.get("elements", [])
        count = 0

        for el in elements:
            actor = el.get("actor", "")
            existing = (
                db.query(Lead)
                .filter(
                    Lead.profile_url == actor,
                    Lead.post_id == post.id,
                    Lead.action == "comment",
                )
                .first()
            )
            if existing:
                continue

            lead = Lead(
                name=actor.split(":")[-1] if actor else "unknown",
                profile_url=f"https://www.linkedin.com/in/{actor.split(':')[-1]}" if actor else "",
                platform="linkedin",
                post_id=post.id,
                action="comment",
                created_at=datetime.now(timezone.utc),
            )
            db.add(lead)
            count += 1

        db.commit()
        return count

    except Exception as exc:
        logger.error("Failed to fetch LinkedIn comments for %s: %s", post.post_id, exc)
        return 0


async def _log_x_likes(post: Post, db: Session, client) -> int:
    """Fetch and store likers for an X post via twikit. Returns count logged."""
    if not post.post_id:
        return 0

    try:
        tweet = await client.get_tweet_by_id(post.post_id)
        users = await tweet.get_favoriters()
        count = 0

        for user in users:
            actor_screen_name = user.screen_name
            existing = (
                db.query(Lead)
                .filter(
                    Lead.platform == "x",
                    Lead.profile_url.like(f"%{actor_screen_name}%"),
                    Lead.post_id == post.id,
                    Lead.action == "like",
                )
                .first()
            )
            if existing:
                continue

            lead = Lead(
                name=getattr(user, "name", actor_screen_name),
                profile_url=f"https://x.com/{actor_screen_name}",
                platform="x",
                post_id=post.id,
                action="like",
                created_at=datetime.now(timezone.utc),
            )
            db.add(lead)
            count += 1

        db.commit()
        return count

    except Exception as exc:
        logger.error("Failed to fetch X likes for %s: %s", post.post_id, exc)
        return 0


async def log_leads_for_recent(db: Session, lookback_days: int = 7) -> None:
    """Log leads from engagement on all posts from the last `lookback_days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    posts = (
        db.query(Post)
        .filter(Post.status == "published", Post.published_at >= cutoff)
        .all()
    )

    logger.info("Logging leads for %d recent posts", len(posts))

    x_client = None

    for post in posts:
        if post.platform == "linkedin":
            likes_count = await _log_linkedin_likes(post, db)
            comments_count = await _log_linkedin_comments(post, db)
            logger.info(
                "LinkedIn post %s: %d new like leads, %d new comment leads",
                post.post_id, likes_count, comments_count,
            )
        elif post.platform == "x":
            if x_client is None:
                from utils.x_client import get_twikit_client
                try:
                    x_client = await get_twikit_client()
                except Exception as exc:
                    logger.error("Skipping X leads logging due to login failure: %s", exc)
                    continue

            likes_count = await _log_x_likes(post, db, x_client)
            logger.info("X post %s: %d new like leads", post.post_id, likes_count)
        else:
            logger.warning("Unknown platform '%s' for post %s", post.platform, post.id)
