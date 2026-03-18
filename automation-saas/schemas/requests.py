from typing import Optional
from pydantic import BaseModel

class TopicCreate(BaseModel):
    topic: str
    platform: str = "both"
    flavor: str = "random"
    personality: str = "random"

class SettingsUpdate(BaseModel):
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    x_api_key: Optional[str] = None
    x_api_secret: Optional[str] = None
    x_access_token: Optional[str] = None
    x_access_token_secret: Optional[str] = None
    x_username: Optional[str] = None
    x_email: Optional[str] = None
    x_password: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    linkedin_urn: Optional[str] = None
    database_url: Optional[str] = None
    admin_api_key: Optional[str] = None
    timezone: Optional[str] = None

class PublishRequest(BaseModel):
    platform: str = "both"  # "x" | "linkedin" | "both"
