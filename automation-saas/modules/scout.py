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
            logger.warning("X scraping (twikit) blocked. Attempting DuckDuckGo fallback for trends.")
            return await get_x_trends_fallback()
        else:
            logger.error(f"Failed to fetch X trends: {e}")
            return await get_x_trends_fallback()

async def get_x_trends_fallback() -> list[str]:
    """Fallback: Search DuckDuckGo for current trends if direct scraping fails."""
    try:
        # Nigeria WOEID is 23424908, region is 'ng'
        query = "current trending topics X twitter Nigeria Lagos today"
        logger.info(f"Fallback: Searching DDG for trends with query: {query}")
        
        with DDGS() as ddgs:
            # Using text search for trends extraction
            results = [r['body'] for r in ddgs.text(query, max_results=10)]
            # Simple heuristic: look for quoted strings or short phrases that look like topics
            trends = []
            for r in results:
                # Basic cleanup: take first few words of search results
                words = r.split()[:5]
                if len(words) >= 2:
                    trends.append(" ".join(words))
            
            clean_trends = list(set(trends))[:8]
            logger.info(f"Fallback: Successfully sourced {len(clean_trends)} surrogate trends.")
            return clean_trends
    except Exception as e:
        logger.error(f"X Trends fallback failed: {e}")
        return ["AI in SaaS", "Remote Work Culture", "Python 3.13 Features", "Lead Magnet Automation"]

async def get_tech_news(query: str = "latest tech news AI software engineering github") -> list[str]:
    """Fetch latest tech news and GitHub finds using DuckDuckGo."""
    try:
        logger.info(f"Searching for news with query: {query}")
        # Use context manager to ensure the internal DDGS client/session is closed
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
