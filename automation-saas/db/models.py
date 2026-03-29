"""
SQLAlchemy ORM models for the Automation SaaS.

Tables: posts, post_metrics, leads, topics
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared base for all models."""
    pass


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(20), nullable=False)          # "x" | "linkedin"
    content = Column(Text, nullable=False)
    post_id = Column(String(100), nullable=True)           # platform-assigned ID
    published_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # published | failed | pending

    metrics = relationship("PostMetric", back_populates="post", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Post {self.platform} {self.status} {self.id}>"


class PostMetric(Base):
    __tablename__ = "post_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    post = relationship("Post", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<PostMetric post={self.post_id} likes={self.likes}>"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=True)
    profile_url = Column(Text, nullable=True)
    platform = Column(String(20), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    action = Column(String(50), nullable=False)            # "like" | "comment"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    post = relationship("Post", back_populates="leads")

    def __repr__(self) -> str:
        return f"<Lead {self.name} {self.action} on {self.platform}>"


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    platform = Column(String, default="both")  # 'x', 'linkedin', 'both'
    tone = Column(String, default="professional")  # deprecated, keeping for legacy
    flavor = Column(String, default="random")     # e.g., 'storytime', 'ragebait', 'hottake', 'random'
    personality = Column(String, default="random") # e.g., 'chaotic', 'professional', 'random'
    is_automated = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Topic '{self.topic[:30]}' {self.platform} active={self.active}>"


class ImageLibrary(Base):
    __tablename__ = "image_library"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    tag = Column(String, index=True) # 'personal', 'headshot', 'infographic', 'meme', 'quote'
    description = Column(Text, nullable=True) # Detailed AI-friendly description
    cloudinary_url = Column(String, nullable=True) # Remote URL if hosted on Cloudinary
    platform_bias = Column(String, default="both") # 'x', 'linkedin', 'both'
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<ImageLibrary {self.filename} tag={self.tag}>"


class WhatsAppState(Base):
    __tablename__ = "whatsapp_state"
    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String, unique=True, index=True)
    state = Column(String, nullable=False) # e.g. "waiting_for_mood"
    temp_image_path = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<WhatsAppState phone={self.user_phone} state={self.state}>"
