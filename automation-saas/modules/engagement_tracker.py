"""
Engagement tracker — fetches post metrics and stores them to the DB.

X:  Free tier does NOT support reading metrics. We store post_id/timestamp only.
LinkedIn: Fetches likes and comments via the socialActions API.

Usage:
    await track_all_recent(db_session, lookback_days=7)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from db.models import Post, PostMetric
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def _linkedin_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


async def _track_linkedin_post(post: Post, db: Session) -> None:
    """Fetch LinkedIn engagement metrics for a single post."""
    if not post.post_id:
        logger.warning("Post %s has no LinkedIn post_id — skipping metrics", post.id)
        return

    try:
        url = f"{LINKEDIN_API_BASE}/socialActions/{post.post_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_linkedin_headers())
            resp.raise_for_status()
            data = resp.json()

        likes = data.get("numLikes", 0)
        comments = data.get("numComments", 0)

        metric = PostMetric(
            post_id=post.id,
            likes=likes,
            comments=comments,
            checked_at=datetime.now(timezone.utc),
        )
        db.add(metric)
        db.commit()

        logger.info(
            "Tracked LinkedIn post %s: %d likes, %d comments",
            post.post_id, likes, comments,
        )

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "LinkedIn metrics fetch failed for %s (HTTP %d)",
            post.post_id, exc.response.status_code,
        )
    except Exception as exc:
        logger.error("Engagement tracking error for %s: %s", post.post_id, exc)


async def _track_x_post(post: Post, db: Session, client) -> None:
    """Fetch X engagement metrics via twikit."""
    if not post.post_id:
        logger.warning("Post %s has no X post_id — skipping metrics", post.id)
        return

    try:
        tweet = await client.get_tweet_by_id(post.post_id)
        
        # twikit Tweet attributes for metrics
        likes = getattr(tweet, "favorite_count", getattr(tweet, "like_count", 0))
        comments = getattr(tweet, "reply_count", 0)

        metric = PostMetric(
            post_id=post.id,
            likes=likes,
            comments=comments,
            checked_at=datetime.now(timezone.utc),
        )
        db.add(metric)
        db.commit()

        logger.info(
            "Tracked X post %s: %d likes, %d comments",
            post.post_id, likes, comments,
        )

    except Exception as exc:
        logger.error("Engagement tracking error for X post %s: %s", post.post_id, exc)


async def track_all_recent(db: Session, lookback_days: int = 7) -> None:
    """Track engagement for all posts from the last `lookback_days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    posts = (
        db.query(Post)
        .filter(Post.status == "published", Post.published_at >= cutoff)
        .all()
    )

    logger.info("Tracking engagement for %d posts (last %d days)", len(posts), lookback_days)

    x_client = None

    for post in posts:
        if post.platform == "linkedin":
            await _track_linkedin_post(post, db)
        elif post.platform == "x":
            # Lazy init X client only if there are X posts
            if x_client is None:
                from utils.x_client import get_twikit_client
                try:
                    x_client = await get_twikit_client()
                except Exception as exc:
                    logger.error("Skipping X posts tracking due to login failure: %s", exc)
                    continue
            
            await _track_x_post(post, db, x_client)
        else:
            logger.warning("Unknown platform '%s' for post %s", post.platform, post.id)
