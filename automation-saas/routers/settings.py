import os
import re
from fastapi import APIRouter, Depends
from utils.config import settings
from core.security import get_current_user
from schemas.requests import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("")
async def get_settings(_: str = Depends(get_current_user)):
    """Fetch current settings from .env (partially masked for safety)."""
    
    def mask(val: str, key: str) -> str:
        if not val: return ""
        # Mask anything with KEY, SECRET, TOKEN, PASS in the name
        sensitive_terms = ["KEY", "SECRET", "TOKEN", "PASS"]
        if any(term in key.upper() for term in sensitive_terms):
            if len(val) <= 8: return "****"
            return val[:8] + "...XXXX"
        return val

    # Convert settings dataclass to dict and mask
    from dataclasses import asdict
    raw_data = asdict(settings)
    masked_data = {k: mask(v, k) for k, v in raw_data.items()}
    
    return masked_data

@router.post("")
async def update_settings(body: SettingsUpdate, _: bool = Depends(get_current_user)):
    """Update settings inside the .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    if not os.path.exists(env_path):
        return {"status": "error", "message": ".env file not found"}

    with open(env_path, "r") as f:
        content = f.read()

    fields_map = {
        "OPENROUTER_API_KEY": body.openrouter_api_key,
        "OPENROUTER_MODEL": body.openrouter_model,
        "X_API_KEY": body.x_api_key,
        "X_API_SECRET": body.x_api_secret,
        "X_ACCESS_TOKEN": body.x_access_token,
        "X_ACCESS_TOKEN_SECRET": body.x_access_token_secret,
        "X_USERNAME": body.x_username,
        "X_EMAIL": body.x_email,
        "X_PASSWORD": body.x_password,
        "LINKEDIN_ACCESS_TOKEN": body.linkedin_access_token,
        "LINKEDIN_PERSON_ID": body.linkedin_urn,
        "DATABASE_URL": body.database_url,
        "ADMIN_API_KEY": body.admin_api_key,
        "TIMEZONE": body.timezone,
        "TOPICS_ENGINE": body.topics_engine,
        "WOEID": body.woeid,
        "X_SCHEDULE_HOURS": body.x_schedule_hours,
        "LI_SCHEDULE_HOURS": body.li_schedule_hours,
    }

    for key, val in fields_map.items():
        if val and not val.startswith("***"):
            if key == "LINKEDIN_PERSON_ID" and ":" in val:
                val = val.split(":")[-1]
            
            content = re.sub(rf'{key}=.*', f'{key}={val}', content)

    with open(env_path, "w") as f:
        f.write(content)

    return {"status": "ok"}
