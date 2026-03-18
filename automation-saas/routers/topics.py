import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.models import Topic
from db.session import get_db
from schemas.requests import TopicCreate
from schemas.responses import TopicResponse
from core.security import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/topics", tags=["Topics"])

@router.post("", response_model=TopicResponse)
async def create_topic(
    body: TopicCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    topic = Topic(
        topic=body.topic,
        platform=body.platform,
        flavor=body.flavor,
        personality=body.personality,
        active=True,
    )
    # The models use 'tone' to store the legacy tone. Let's ensure it's a string.
    topic.tone = body.flavor 
    db.add(topic)
    db.commit()
    db.refresh(topic)
    logger.info("Created topic: %s (%s)", topic.topic, topic.platform)
    # Topic.id is integer. In TopicResponse it's defined as str. Make sure TopicResponse allows coercion via Config.
    return topic

@router.put("/{topic_id}/toggle", response_model=TopicResponse)
async def toggle_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic.active = not topic.active
    db.commit()
    db.refresh(topic)
    logger.info("Toggled topic %s → active=%s", topic.id, topic.active)
    return topic
