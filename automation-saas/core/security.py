import logging
from fastapi import Header, HTTPException, Request
from utils.config import settings

logger = logging.getLogger(__name__)

async def verify_api_key(request: Request, x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Validate the admin API key from request headers or session cookie."""
    cookie_token = request.cookies.get("session_token")
    
    # 1. Resolve which token to use (header takes priority if it has a real value)
    # Ignore junk strings like "null", "undefined", or empty string from headers
    if x_api_key and x_api_key.lower() not in ["null", "undefined", "none", ""]:
        api_key = x_api_key.strip()
    else:
        api_key = cookie_token.strip() if cookie_token else None
    
    # 2. Compare against settings (also stripped for safety)
    expected = settings.ADMIN_API_KEY.strip()
    
    if api_key != expected:
        logger.warning(
            f"Auth failed. Header present: {bool(x_api_key)}, "
            f"Cookie present: {bool(cookie_token)}, "
            f"Key mismatch (len: {len(api_key or '')} vs {len(expected)})"
        )
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key

async def get_current_user(request: Request):
    """Check session cookie or header for UI/API access."""
    return await verify_api_key(request)
