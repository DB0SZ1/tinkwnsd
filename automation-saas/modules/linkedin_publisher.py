"""
LinkedIn publisher — posts to a personal LinkedIn profile via the official API.

Uses the ugcPosts endpoint with OAuth 2.0 (access token from .env).

Usage:
    post_record = await publish_to_linkedin("Post text here", db_session)
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from db.models import Post
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


async def _get_person_urn() -> str:
    """Resolve the LinkedIn person URN.

    Uses LINKEDIN_PERSON_ID from config if set, otherwise fetches from /v2/me.
    """
    if settings.LINKEDIN_PERSON_ID:
        return f"urn:li:person:{settings.LINKEDIN_PERSON_ID}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{LINKEDIN_API_BASE}/me", headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        return f"urn:li:person:{data['id']}"


async def _upload_image_to_linkedin(image_path: str, person_urn: str) -> str | None:
    """Executes LinkedIn's 3-step image upload process."""
    import os
    import aiofiles
    
    if not os.path.exists(image_path):
        logger.error("Image file not found: %s", image_path)
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Register Upload
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": person_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            reg_resp = await client.post(
                f"{LINKEDIN_API_BASE}/assets?action=registerUpload",
                json=register_payload,
                headers=_headers()
            )
            reg_resp.raise_for_status()
            reg_data = reg_resp.json()
            
            upload_url = reg_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_urn = reg_data["value"]["asset"]
            
            # 2. Upload Image Binary
            async with aiofiles.open(image_path, "rb") as f:
                image_data = await f.read()
                
            upload_resp = await client.put(
                upload_url,
                content=image_data,
                headers={"Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}"}
            )
            upload_resp.raise_for_status()
            logger.info("Uploaded LinkedIn image asset: %s", asset_urn)
            
            return asset_urn
    except Exception as exc:
        logger.error("LinkedIn image upload failed: %s", exc)
        return None


async def publish_to_linkedin(text: str, db: Session, image_path: str | None = None) -> Post | None:
    """Publish a text/image post to LinkedIn /v2/posts and persist the record."""
    post = Post(
        platform="linkedin",
        content=text,
        status="pending",
    )

    try:
        person_urn = await _get_person_urn()
        asset_urn = None
        
        if image_path:
            asset_urn = await _upload_image_to_linkedin(image_path, person_urn)

        # /v2/posts Payload Strategy
        payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            }
        }
        
        if asset_urn:
            payload["content"] = {
                "media": [
                    {
                        "id": asset_urn,
                        "altText": "Image for LinkedIn post"
                    }
                ]
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LINKEDIN_API_BASE}/posts",
                json=payload,
                headers=_headers(),
            )
            resp.raise_for_status()
            
            # LinkedIn returns post URN in the 'x-restli-id' header (201 Created with empty body)
            linkedin_post_id = resp.headers.get("x-restli-id")
            if not linkedin_post_id:
                try:
                    data = resp.json()
                    linkedin_post_id = data.get("id", "")
                except Exception:
                    linkedin_post_id = ""
        post.post_id = linkedin_post_id
        post.published_at = datetime.now(timezone.utc)
        post.status = "published"

        db.add(post)
        db.commit()
        db.refresh(post)

        logger.info("Published modern LinkedIn post %s (id=%s)", post.id, linkedin_post_id)
        return post

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 401:
            logger.error(
                "LinkedIn token expired (401). Halt LinkedIn publishing. "
                "Refresh LINKEDIN_ACCESS_TOKEN in .env."
            )
        elif status_code == 429:
            logger.warning("LinkedIn rate limit (429). Skipping — will resume next run.")
        else:
            logger.error("LinkedIn API error %d: %s", status_code, exc, exc_info=True)

        post.status = "failed"
        db.add(post)
        db.commit()
        return None

    except Exception as exc:
        logger.error("LinkedIn publish failed: %s", exc, exc_info=True)
        post.status = "failed"
        db.add(post)
        db.commit()
        return None

async def check_li_auth() -> dict:
    """Verifies LinkedIn connectivity and token health."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{LINKEDIN_API_BASE}/me", headers=_headers())
            if resp.status_code == 200:
                data = resp.json()
                return {"status": "healthy", "user": data.get("localizedFirstName", "User")}
            else:
                return {"status": "unauthorized", "error": resp.text[:100]}
    except Exception as e:
        return {"status": "error", "error": str(e)}
