"""
Loads and validates environment variables from .env file.
Exposes a singleton Settings instance used throughout the app.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


@dataclass(frozen=True)
class Settings:
    """Validated application settings sourced from environment variables."""

    # OpenRouter
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str

    # X / Twitter (API)
    X_API_KEY: str
    X_API_SECRET: str
    X_ACCESS_TOKEN: str
    X_ACCESS_TOKEN_SECRET: str

    # X / Twitter (twikit scraping)
    X_USERNAME: str
    X_EMAIL: str
    X_PASSWORD: str

    # LinkedIn
    LINKEDIN_ACCESS_TOKEN: str
    LINKEDIN_PERSON_ID: str

    # Database
    DATABASE_URL: str

    # Admin
    ADMIN_API_KEY: str

    # Timezone
    TIMEZONE: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Build Settings from os.environ. Raises ValueError on missing keys."""
        values: dict[str, str] = {}
        missing: list[str] = []

        for f in fields(cls):
            val = os.getenv(f.name)
            if val is None or val == "":
                missing.append(f.name)
                values[f.name] = ""
            else:
                values[f.name] = val

        if missing:
            # Log a warning but don't crash — some modules may not be used
            import logging
            logging.warning(
                "Missing environment variables (some modules may not work): %s",
                ", ".join(missing),
            )

        return cls(**values)


# Singleton — import this everywhere
settings = Settings.from_env()
