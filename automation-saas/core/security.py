import logging
from fastapi import Header, HTTPException, Request
from utils.config import settings

logger = logging.getLogger(__name__)

async def verify_api_key(request: Request, x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Validate the admin API key from request headers or session cookie."""
    cookie_token = request.cookies.get("session_token")
    api_key = x_api_key or cookie_token
    
    if api_key != settings.ADMIN_API_KEY:
        logger.warning(f"Auth failed. Header key: {bool(x_api_key)}, Cookie key found: {bool(cookie_token)}")
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key

async def get_current_user(request: Request):
    """Check session cookie or header for UI/API access."""
    return await verify_api_key(request)
