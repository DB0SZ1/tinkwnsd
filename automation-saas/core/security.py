from fastapi import Header, HTTPException, Request
from utils.config import settings

async def verify_api_key(request: Request, x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Validate the admin API key from request headers or session cookie."""
    api_key = x_api_key or request.cookies.get("session_token")
    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

async def get_current_user(request: Request):
    """Check session cookie or header for UI/API access."""
    return await verify_api_key(request)
