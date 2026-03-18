"""
Content generator — calls OpenRouter to produce platform-appropriate posts.

Usage:
    text = await generate_content("AI agent failures", platform="x", tone="founder")
"""

from __future__ import annotations

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPTS = {
    "x": (
        "You are a social-media copywriter for X (Twitter). "
        "Rules: max 280 characters total, punchy and direct, hook in the first line, "
        "no hashtag spam (1 hashtag max), no emojis unless they add meaning. "
        "Return ONLY the tweet text, nothing else."
    ),
    "linkedin": (
        "You are a LinkedIn thought-leadership writer. "
        "Rules: 150–300 words, insight-driven, professional but human tone, "
        "end with a question or call-to-action to drive comments. "
        "Return ONLY the post text, nothing else."
    ),
}

TONE_INSTRUCTIONS = {
    "technical": "Write in a precise, technical voice. Use data and specifics.",
    "founder": "Write from the perspective of a startup founder sharing hard-won lessons.",
    "casual": "Write in a relaxed, conversational tone as if talking to a friend.",
}




async def generate_content(topic: str, platform: str = "x", flavor: str = "random", personality: str = "random") -> str:
    """
    Generate platform-specific content using OpenRouter AI.
    Features: Content Persona Layering, Platform Tone Calibration, Human Signals.
    """
    # Auto-randomize if 'random'
    import random
    if flavor == "random":
        valid_flavors = ["storytime", "hottake", "foodthought", "update", "ragebait", "tips"]
        flavor = random.choice(valid_flavors)
        
    if personality == "random":
        valid_personalities = ["chaotic", "professional", "experimental", "chill"]
        personality = random.choice(valid_personalities)

    # 1. Platform Tone Calibration
    if platform == "linkedin":
        rules = (
            "- **Tone:** Professional but warm. Storytelling ✅. No slang. Hot takes should be toned down.\n"
            "- **Format:** Short paragraphs (1-2 sentences each). Use 1-2 relevant emojis.\n"
            "- **Ending:** End with a genuine question to drive comments."
        )
        if flavor == "ragebait":
            flavor = "hottake" # LinkedIn is too professional for pure ragebait
    elif platform == "x":
        rules = (
            "- **Tone:** Full personality. Shorter, punchier sentences. Lowercase casual is okay.\n"
            "- **Constraints:** MUST be under 280 characters. Be concise.\n"
            "- **Ending:** Drop a mic, no standard 'what do you think' questions."
        )
    else:  # 'both' or others
        rules = "- **Tone:** A mix. Casual but insightful. Not too long."

    # 2. Add "Human Signals" based on personality mode
    if personality == "chaotic":
        rules += "\n- **Human Signals:** Use lowercase often. Be slightly provocative or mischievous."
    elif personality == "professional":
        rules += "\n- **Human Signals:** Clear, structured insights. Use narrative arcs."
    elif personality == "chill":
        rules += "\n- **Human Signals:** Treat the reader like a friend. Use imperfect openers like 'Okay so hear me out...' or 'Not gonna lie...'"
    else: # experimental
        rules += "\n- **Human Signals:** Use cliffhangers or self-referential notes like 'I posted about this last week but...'"

    # Combine into system prompt
    system_prompt = f"""You are a top-tier social media content creator writing for an automated bot persona.
Do NOT sound like a robot, AI assistant, or marketer.
Write a post for {platform.upper()}.

# Setup
- Topic: {topic}
- Flavor: {flavor.upper()} (Wrap the topic in this style)
- Personality: {personality.upper()}

# Platform & Human Rules
{rules}

# Output format
Return ONLY the raw post content. No preambles, no quotes around the text, no hashtags unless naturally fitting. Just the text to be published."""

    logger.debug(
        "Generating %s content for topic: '%s' (flavor: %s, mode: %s)",
        platform, topic, flavor, personality
    )

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(timeout=30.0) as client:
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
                                {"role": "user", "content": f"Write the post about: {topic}"},
                            ],
                            "temperature": 0.75, # slightly higher for creativity
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"].strip()
                        # Final safety clamp for X
                        if platform == "x" and len(content) > 280:
                            content = content[:277] + "..."
                        return content
                    else:
                        raise ValueError(f"Unexpected OpenRouter response: {data}")

    except Exception as exc:
        logger.error("Content generation failed: %s", exc)
        return f"Could not generate post about {topic[:20]}..."
