from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.models import Lead
from db.session import get_db
from schemas.responses import LeadResponse
from core.security import verify_api_key

router = APIRouter(prefix="/leads", tags=["Leads"])

@router.get("", response_model=list[LeadResponse])
async def list_leads(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
    limit: int = Query(50, ge=1, le=200),
):
    leads = (
        db.query(Lead)
        .order_by(Lead.created_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [
        LeadResponse(
            id=str(l.id),
            name=l.name,
            profile_url=l.profile_url,
            platform=l.platform,
            post_id=str(l.post_id),
            action=l.action,
            created_at=l.created_at.isoformat() if l.created_at else None,
        )
        for l in leads
    ]
