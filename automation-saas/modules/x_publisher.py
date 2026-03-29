"""
X (Twitter) publisher — posts tweets via the free write-only API.

Limits:
  - 500 posts/month on free tier (~16/day, we use max 2/day)
  - Write-only: cannot read timeline or replies

Usage:
    post_record = await publish_to_x("Some tweet text", db_session)
"""

from __future__ import annotations

from datetime import datetime, timezone

import tweepy

from db.models import Post
from sqlalchemy.orm import Session
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_client() -> tweepy.Client:
    """Build an authenticated tweepy Client."""
    return tweepy.Client(
        consumer_key=settings.X_API_KEY,
        consumer_secret=settings.X_API_SECRET,
        access_token=settings.X_ACCESS_TOKEN,
        access_token_secret=settings.X_ACCESS_TOKEN_SECRET,
    )


async def publish_to_x(text: str, db: Session, image_path: str | None = None) -> Post | None:
    """Publish a tweet and persist the record.

    Args:
        text: Tweet text (truncated to 280 chars).
        db: Active SQLAlchemy session.
        image_path: Optional local path to an image to attach.

    Returns:
        The Post record on success, or None on failure.
    """
    if len(text) > 280:
        text = text[:277] + "..."

    post = Post(
        platform="x",
        content=text,
        status="pending",
    )

    try:
        client = _get_client()
        media_ids = None

        if image_path:
            # Tweepy V2 client doesn't support media_upload directly yet.
            # We must use V1.1 API via OAuth1UserHandler for media upload.
            auth = tweepy.OAuth1UserHandler(
                settings.X_API_KEY, settings.X_API_SECRET,
                settings.X_ACCESS_TOKEN, settings.X_ACCESS_TOKEN_SECRET
            )
            api = tweepy.API(auth)
            media = api.media_upload(image_path)
            media_ids = [media.media_id]
            logger.info("Uploaded media for X: %s", media.media_id)

        if media_ids:
            response = client.create_tweet(text=text, media_ids=media_ids)
        else:
            response = client.create_tweet(text=text)
            
        tweet_id = str(response.data["id"])

        post.post_id = tweet_id
        post.published_at = datetime.now(timezone.utc)
        post.status = "published"

        db.add(post)
        db.commit()
        db.refresh(post)

        logger.info("Published tweet %s (id=%s)", post.id, tweet_id)
        return post

    except tweepy.TooManyRequests:
        logger.warning("X rate limit hit (429). Standard Apps have lower limits. Skipping.")
        post.status = "failed"
        db.add(post)
        db.commit()
        return None

    except tweepy.Unauthorized:
        logger.error("X authentication failed. Ensure your 'Standard App' has 'Read and Write' permissions enabled in the User authentication settings.")
        post.status = "failed"
        db.add(post)
        db.commit()
        return None

    except Exception as exc:
        logger.error("X publish failed with exception: %s", type(exc).__name__)
        # If it's a Forbidden 403, it's often due to lack of Write permissions
        if "403" in str(exc):
            logger.error("403 Forbidden: CHECK YOUR APP PERMISSIONS. Standard Apps must have 'Read and Write' enabled.")
        logger.error("Full traceback log: %s", exc, exc_info=True)
        post.status = "failed"
        db.add(post)
        db.commit()
        return None
