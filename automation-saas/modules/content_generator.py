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
        valid_personalities = ["visionary", "analyst", "comedian", "mentor", "skeptic", "hype-beast", "chill", "chaotic"]
        personality = random.choice(valid_personalities)

    # 1. Platform Tone Calibration
    if platform == "linkedin":
        rules = (
            "- **Tone:** Professional but deeply human. Storytelling is mandatory. No dry corporate speak.\n"
            "- **Format:** Use plenty of white space. 1-2 sentences per paragraph.\n"
            "- **Engagement:** End with a question that feels like a conversation starter, not a marketing survey."
        )
    elif platform == "x":
        rules = (
            "- **Tone:** High signal-to-noise. Be punchy. Use lowercase for casual vibes if appropriate.\n"
            "- **Constraints:** Strictly under 280 characters.\n"
            "- **Vibe:** Sharp, witty, and immediate."
        )
    else: 
        rules = "- **Tone:** Balanced. Engaging and clear."

    # 2. Personality Depth & Human Signals
    if personality == "visionary":
        rules += "\n- **Persona:** You see the future. Talk about 'what's next' and 'the big picture'. Be inspiring and slightly idealistic."
        rules += "\n- **Human Signals:** Use words like 'imagine', 'possibility', 'tomorrow'. Avoid jargon."
    elif personality == "analyst":
        rules += "\n- **Persona:** You are skeptical and data-obsessed. Break things down. Be precise and realistic."
        rules += "\n- **Human Signals:** Use phrases like 'the reality is', 'the math doesn't add up', 'here is the actual breakdown'."
    elif personality == "comedian":
        rules += "\n- **Persona:** You don't take anything seriously. Use irony, self-deprecation, and wit."
        rules += "\n- **Human Signals:** Use 'tbh', 'lol', or dry observations about how ridiculous things are."
    elif personality == "mentor":
        rules += "\n- **Persona:** You want to help. Share lessons, avoid ego, be warm and encouraging."
        rules += "\n- **Human Signals:** Use 'I wish I knew this earlier', 'Here is a small tip', 'You've got this'."
    elif personality == "skeptic":
        rules += "\n- **Persona:** You are the contrarian. Challenge the status quo. Be respectfully blunt."
        rules += "\n- **Human Signals:** Use 'Is it just me or...', 'Unpopular opinion:', 'We need to stop pretending that...'."
    elif personality == "hype-beast":
        rules += "\n- **Persona:** High energy. Everything is amazing. Be the ultimate cheerleader."
        rules += "\n- **Human Signals:** Use all-caps for emphasis occasionally. Use '!'. Be very promotional but authentic."
    elif personality == "chaotic":
        rules += "\n- **Persona:** Mischievous and unpredictable. Break the fourth wall. Be slightly weird."
        rules += "\n- **Human Signals:** Start mid-thought. Use chaotic formatting. Be unapologetically you."
    elif personality == "chill":
        rules += "\n- **Persona:** Relaxed, low-stakes, effortlessly cool. Like a Sunday morning coffee chat."
        rules += "\n- **Human Signals:** Use soft openers like 'just thinking about...', 'honestly...', 'no pressure but...'."

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
