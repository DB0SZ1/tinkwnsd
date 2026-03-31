"""
Content generator — calls OpenRouter to produce platform-appropriate posts.

Usage:
    text = await generate_content("AI agent failures", platform="x", tone="founder")
"""

from __future__ import annotations

import os
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

def _load_persona_context() -> str:
    """Read the 3 core .md files in the persona/ directory to build the AI's system context."""
    persona_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "persona")
    # Only the 3 core files as requested
    files = ["persona.md", "how_to_write.md", "memory.md"]
    context = []
    
    for f_name in files:
        f_path = os.path.join(persona_dir, f_name)
        if os.path.exists(f_path):
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    context.append(f"### {f_name.upper()} ###\n{content}")
            except Exception as e:
                logger.error(f"Failed to read persona file {f_name}: {e}")
                
    return "\n\n".join(context)

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




async def generate_content(
    topic: str, 
    platform: str = "x", 
    flavor: str = "random", 
    personality: str = "random",
    context: str | None = None
) -> tuple[str, str | None]:
    """
    Generate platform-specific content using OpenRouter AI.
    Features: Content Persona Layering, Platform Tone Calibration, Human Signals, Real-time Context.
    """
    import random
    
    # 1. Expand Personalities (Strategic for lead gen)
    valid_personalities = [
        "visionary", "analyst", "comedian", "mentor", "skeptic", 
        "hype-beast", "chill", "chaotic", "github-discoverer",
        "10x-shipper", "work-advertiser", "trend-analyst", "lead-magnet"
    ]
    
    if personality == "random" or personality not in valid_personalities:
        personality = random.choice(valid_personalities)

    if flavor == "random":
        valid_flavors = ["storytime", "hottake", "foodthought", "update", "ragebait", "tips", "tutorial", "case-study"]
        flavor = random.choice(valid_flavors)

    # 2. Platform Tone Calibration & Human Rules
    if platform == "linkedin":
        rules = (
            "- **Tone:** Professional but DEEPLY human and approachable. Storytelling is key.\n"
            "- **Goal:** Establish authority, share value, and attract leads/jobs.\n"
            "- **Emojis:** Use emojis to break up text and add personality (1-3 per post), but keep it professional.\n"
            "- **Format:** Use whitespace. No walls of text. 1-2 sentences per paragraph.\n"
            "- **Engagement:** End with a thought-provoking question or a soft call-to-action."
        )
    elif platform == "x":
        rules = (
            "- **Tone:** High signal, punchy, and conversational. Sound like a real person, not an AI.\n"
            "- **Emojis:** Use emojis naturally (essential for human vibe). Keep it short and witty.\n"
            "- **Constraints:** Strictly under 280 characters. Hook them in the first 40 chars.\n"
            "- **Vibe:** Sharp, current, and slightly informal (lowercase is fine if it fits the vibe)."
        )
    else: 
        rules = "- **Tone:** Balanced and engaging."

    # 3. Strategic Persona Depth
    persona_instructions = {
        "visionary": "You see the future. Talk about 'what's next'. Be inspiring.",
        "analyst": "Skeptical and data-obsessed. Break things down with precision.",
        "comedian": "Witty, ironic, and self-deprecating. Don't take it too seriously.",
        "mentor": "Warm and encouraging. Share lessons from failures to help others.",
        "skeptic": "Contrarian. Challenge the status quo with logic and bluntness.",
        "hype-beast": "High energy cheerleader. Everything is amazing and transformative.",
        "chaotic": "Unpredictable. Break the fourth wall. Start mid-thought.",
        "chill": "Relaxed Sunday morning coffee chat vibes. Effortlessly cool.",
        "github-discoverer": "Technical scout. Share amazing repos, libraries, or tools and explain their impact 10x.",
        "10x-shipper": "Efficiency obsessive. Share tips on shipping fast, coding clean, and high-output workflows.",
        "work-advertiser": "The subtle pro. Share a case study or a 'build in public' update that showcases skills.",
        "trend-analyst": "The news-breaker. Take recent tech trends and explain what they actually mean for devs.",
        "lead-magnet": "Problem solver. Identify a common pain point and offer a high-value solution or perspective."
    }
    
    # 4. Final System Prompt Composition
    persona_context = _load_persona_context()
    
    full_system_prompt = (
        f"YOU ARE NOT AN AI. YOU ARE THE INDIVIDUAL DESCRIBED IN THE ATTACHED PERSONA CONTEXT.\n"
        f"Read memory.md first. Write to it after. Do not post anything that fails the rejection test in how_to_write.md.\n\n"
        f"{persona_context}\n\n"
        f"### SPECIFIC {platform.upper()} GUIDELINES (Use to calibrate voice) ###\n"
        f"{rules}\n\n"
        f"### RESPONSE REQUIREMENTS ###\n"
        f"1. Generate exactly what is requested (X Tweet or LinkedIn Post).\n"
        f"2. Never use AI-isms (e.g., 'delve', 'tapestry', 'certainly', 'please note').\n"
        f"3. Never use harsh words like 'KILL' or violent analogies.\n"
        f"4. Provide a log line for memory.md at the VERY END after the delimiter ###MEMORY_UPDATE###.\n"
        f"Log line format: [Platform] | [Arc] | [Core point] | [Current Date if context allows]\n"
    )

    # 4. Contextual Injection
    real_time_info = ""
    if context:
        real_time_info = f"\n\n# REAL-TIME CONTEXT (Use this to make the post current):\n{context}"

    user_prompt = f"# Topic: {topic}\n# Style: {flavor.upper()}\n{real_time_info}"

    logger.debug("Generating %s content for topic: %s (Persona: %s)", platform, topic, personality)

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        OPENROUTER_URL,
                        headers={
                            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.OPENROUTER_MODEL,
                            "messages": [
                                {"role": "system", "content": full_system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.8,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if "choices" in data and len(data["choices"]) > 0:
                        raw_content = data["choices"][0]["message"]["content"].strip()
                        
                        # Parse post vs memory log
                        if "###MEMORY_UPDATE###" in raw_content:
                            post_part, memory_part = raw_content.split("###MEMORY_UPDATE###")
                            content = post_part.strip()
                            memory_log = memory_part.strip().strip("|") # Clean up
                        else:
                            content = raw_content
                            memory_log = None
                            
                        # Safety clamp for X
                        if platform == "x" and len(content) > 280:
                            content = content[:277] + "..."
                        return (content, memory_log)
                    else:
                        raise ValueError(f"Unexpected OpenRouter response: {data}")

    except Exception as exc:
        logger.error("Content generation failed: %s", exc)
        # Return a safe tuple — never the generic slop
        if platform == "x":
            fallback = f"Been deep in {topic}. More on this soon."
        else:
            fallback = f"Working on something around {topic}. Will share details once it's ready."
        return (fallback, None)
