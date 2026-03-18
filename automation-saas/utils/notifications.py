"""
Push notifications via ntfy.sh (100% free, no auth required).
"""

from __future__ import annotations

import httpx

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# To receive these, the user just downloads the NTFY app and subscribes to this topic.
# We prefix with 'donezo_saas_' and append the admin key hash or a static string to keep it private but accessible.
# For simplicity, we'll use a hardcoded topic or let the user define it in .env.
# If nothing is defined, we hash the first 8 chars of the admin key.
if settings.ADMIN_API_KEY:
    NTFY_TOPIC = getattr(settings, "NTFY_TOPIC", f"donezo_saas_{settings.ADMIN_API_KEY[:8]}")
else:
    NTFY_TOPIC = "donezo_saas_default"


async def send_push_notification(title: str, message: str, priority: int = 3, tags: str = "") -> None:
    """
    Send a push notification via ntfy.sh.
    priority: 1 (min) to 5 (max)
    tags: comma separated emojis or tag words (e.g., 'warning,skull')
    """
    headers = {
        "Title": title,
        "Priority": str(priority),
    }
    if tags:
        headers["Tags"] = tags

    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=message.encode('utf-8'), headers=headers)
            resp.raise_for_status()
            logger.debug("Push notification sent: %s", title)
    except Exception as exc:
        logger.error("Failed to send push notification: %s", exc)

def send_push_notification_sync(title: str, message: str, priority: int = 3, tags: str = "") -> None:
    """Sync wrapper for sending push notifications from APScheduler."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_push_notification(title, message, priority, tags))
    except RuntimeError:
        # No running loop, run until complete
        asyncio.run(send_push_notification(title, message, priority, tags))
