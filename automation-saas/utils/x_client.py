"""
Shared X (Twitter) client for scraping metrics and leads via twikit.
"""

from __future__ import annotations

from twikit import Client

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_twikit_client() -> Client:
    """Initialize and log in to a twikit Client."""
    if not all([settings.X_USERNAME, settings.X_EMAIL, settings.X_PASSWORD]):
        logger.error("Missing X twikit credentials (USERNAME, EMAIL, PASSWORD)")
        raise ValueError("Missing X credentials for twikit")

    client = Client(language="en-US")
    logger.info("Logging into X via twikit for user %s...", settings.X_USERNAME)
    
    # twikit login requires auth_info_1 (username/email), auth_info_2 (email/username), password
    await client.login(
        auth_info_1=settings.X_USERNAME,
        auth_info_2=settings.X_EMAIL,
        password=settings.X_PASSWORD,
    )
    
    logger.info("Successfully logged into X via twikit")
    return client
