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
    # 1. Detailed Diagnostic Logging (Masked)
    def mask(s): return f"{s[:4]}...{s[-4:]}" if s and len(s) > 8 else "****"
    
    logger.info("--- X AUTH DIAGNOSTIC START ---")
    logger.info(f"API Key: {mask(settings.X_API_KEY)}")
    logger.info(f"API Secret: {mask(settings.X_API_SECRET)}")
    logger.info(f"Access Token: {mask(settings.X_ACCESS_TOKEN)}")
    logger.info(f"Access Token Secret: {mask(settings.X_ACCESS_TOKEN_SECRET)}")
    
    try:
        # Standard App (v2 API) requires OAuth 1.0a User Context for POST /2/tweets
        client = tweepy.Client(
            consumer_key=settings.X_API_KEY.strip(),
            consumer_secret=settings.X_API_SECRET.strip(),
            access_token=settings.X_ACCESS_TOKEN.strip(),
            access_token_secret=settings.X_ACCESS_TOKEN_SECRET.strip(),
            wait_on_rate_limit=True
        )
        
        # Verify credentials by getting me (User ID)
        me = client.get_me()
        if me and me.data:
            logger.info(f"X Auth SUCCESS: Authenticated as @{me.data.username} (ID: {me.data.id})")
        else:
            logger.warning("X Auth PARTIAL: Connected but could not fetch user profile.")
        
        return client

    except Exception as e:
        logger.error(f"X Auth FAILURE: {e}")
        if "401" in str(e):
            logger.error("DIAGNOSTIC: Error 401 Unauthorized. This usually means your Access Token/Secret are invalid OR you regenerated them but didn't update the .env.")
        elif "403" in str(e):
            logger.error("DIAGNOSTIC: Error 403 Forbidden. This usually means your App does NOT have 'Read and Write' permissions enabled in the X Developer Portal.")
        elif "400" in str(e):
            logger.error("DIAGNOSTIC: Error 400 Bad Request. Check for hidden spaces/newlines in your .env keys.")
        
        raise  # Re-raise to show the "Manual Guide" below


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
