"""
Image selection utility — matching post content to the best library image.
"""

from __future__ import annotations
import httpx
import random
from sqlalchemy.orm import Session
from db.models import ImageLibrary
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

async def select_best_image(content: str, db: Session) -> str | None:
    """
    Select the best image matching the content based on descriptions.
    Uses a quick LLM call to match vibes/keywords.
    """
    try:
        images = db.query(ImageLibrary).all()
        if not images:
            return None
            
        # Filter for images with descriptions
        image_pool = [img for img in images if img.description]
        if not image_pool:
            # Fallback: Pick a random image from the entire library if no descriptions exist
            return random.choice(images).filename

        # Construct a list of descriptions for the AI
        options = "\n".join([f"- {i.filename}: {i.description}" for i in image_pool])
        
        system_prompt = (
            "You are a visual content curator. Given a social media post and a list of images (filename: description), "
            "select the filename of the ONE image that best matches the post's topic or vibe. "
            "Return ONLY the filename. If no image matches at all, return 'NONE'."
        )
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Post Content: {content}\n\nAvailable Images:\n{options}"},
                    ],
                    "temperature": 0.0, # Deterministic for matching
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                selection = data["choices"][0]["message"]["content"].strip()
                if selection.upper() == "NONE":
                    logger.info("AI found no suitable image match. Skipping image.")
                    return None
                
                # Verify the filename exists in our pool to be safe
                for img in image_pool:
                    if img.filename in selection:
                        logger.info(f"AI matched post to image: {img.filename}")
                        return img.filename
                        
        logger.warning("AI selection did not match any known filename. Falling back.")
        return None
    except Exception as e:
        logger.error(f"Image selection failed: {e}")
        return None
