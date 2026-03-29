"""
Scout module — fetches real-time trends and news to power the Automatic Topics Engine.
Uses twikit for X trends and DuckDuckGo for tech news.
"""

from __future__ import annotations
import asyncio
import random
from twikit import Client
from duckduckgo_search import DDGS
# Silence the rename warning if possible, though DDGS() is the new way.
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

async def get_x_trends() -> list[str]:
    """Fetch regional trends from X using twikit (Scraping-based)."""
    if not settings.X_USERNAME or not settings.X_PASSWORD:
        logger.warning("X (twikit) credentials not set. Skipping X trends scouting.")
        return []

    client = Client('en-US')
    try:
        # twikit login is asynchronous
        await client.login(
            auth_info_1=settings.X_USERNAME,
            auth_info_2=settings.X_EMAIL,
            password=settings.X_PASSWORD
        )
        
        # Nigeria WOEID is 23424908 (default in settings)
        woeid = int(settings.WOEID) if settings.WOEID else 23424908
        
        logger.info(f"Fetching X trends for WOEID: {woeid}")
        place_trends = await client.get_place_trends(woeid=woeid)
        
        # place_trends is usually a list of dicts or objects depending on twikit version
        # Some versions return a list directly, some a PlaceTrends object.
        # Based on research, it's often a list of trends.
        trends = []
        if hasattr(place_trends, 'trends'):
            trends = [t.name for t in place_trends.trends]
        elif isinstance(place_trends, list):
            trends = [t.get('name') or t.name for t in place_trends]
        
        clean_trends = [t for t in trends if t][:10]
        logger.info(f"Successfully fetched {len(clean_trends)} X trends.")
        return clean_trends
    except Exception as e:
        if "KEY_BYTE indices" in str(e):
            logger.error("X scraping (twikit) blocked or interrupted. X internal indices changed.")
        else:
            logger.error(f"Failed to fetch X trends: {e}", exc_info=True)
        return []

async def get_tech_news(query: str = "latest tech news AI software engineering github") -> list[str]:
    """Fetch latest tech news and GitHub finds using DuckDuckGo."""
    try:
        logger.info(f"Searching for news with query: {query}")
        # The new ddgs package prefers this non-context-manager approach or just DDGS().news()
        with DDGS() as ddgs:
            results = [r for r in ddgs.news(query, max_results=8)]
            news = [f"{r['title']} - {r['body'][:200]}..." for r in results]
            logger.info(f"Successfully fetched {len(news)} news items.")
            return news
    except Exception as e:
        logger.error(f"Failed to fetch tech news: {e}")
        return []

async def get_trending_context() -> str:
    """Gather a string of trending context to feed into the AI content generator."""
    x_trends = await get_x_trends()
    tech_news = await get_tech_news()
    
    context_parts = []
    if x_trends:
        context_parts.append(f"CURRENT X TRENDS (Nigeria/Regional): {', '.join(x_trends)}")
    if tech_news:
        context_parts.append(f"LATEST TECH/AI NEWS: {' | '.join(tech_news)}")
        
    if not context_parts:
        return "No real-time trends found. Use general high-value tech topics."
        
    return "\n\n".join(context_parts)

if __name__ == "__main__":
    # Quick test
    async def test():
        ctx = await get_trending_context()
        print(ctx)
    asyncio.run(test())
