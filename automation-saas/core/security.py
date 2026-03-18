from fastapi import Header, HTTPException, Request
from utils.config import settings

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate the admin API key from request headers."""
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

async def get_current_user(request: Request):
    """Check session cookie for UI access. Can also fallback to header if needed."""
    session_token = request.cookies.get("session_token")
    if session_token and session_token == settings.ADMIN_API_KEY:
        return True
    x_api_key = request.headers.get("X-API-Key")
    if x_api_key and x_api_key == settings.ADMIN_API_KEY:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")
