from typing import Optional
from pydantic import BaseModel
import uuid

class TopicResponse(BaseModel):
    id: int
    topic: str
    platform: str
    flavor: str
    personality: str
    is_automated: bool
    active: bool

    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: uuid.UUID
    platform: str
    content: str
    post_id: Optional[str] = None
    published_at: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class LeadResponse(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    profile_url: Optional[str] = None
    platform: str
    post_id: str
    action: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
