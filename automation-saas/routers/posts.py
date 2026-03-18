from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.models import Post
from db.session import get_db
from schemas.responses import PostResponse
from core.security import verify_api_key

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.get("", response_model=list[PostResponse])
async def list_posts(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
    limit: int = Query(50, ge=1, le=200),
):
    posts = (
        db.query(Post)
        .order_by(Post.published_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    # Convert dates to strings and IDs to strings implicitly via Pydantic model validation.
    return [
        PostResponse(
            id=str(p.id),
            platform=p.platform,
            content=p.content,
            post_id=p.post_id,
            published_at=p.published_at.isoformat() if p.published_at else None,
            status=p.status,
        )
        for p in posts
    ]
