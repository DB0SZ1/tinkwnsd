from twilio.rest import Client
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

def get_client():
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return None
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to_number: str, message: str) -> bool:
    """Send a WhatsApp message via Twilio."""
    client = get_client()
    if not client:
        logger.warning("Twilio is not configured. Cannot send WhatsApp message.")
        return False
        
    try:
        from_number = settings.TWILIO_WHATSAPP_NUMBER
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"
            
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        msg = client.messages.create(
            from_=from_number,
            body=message,
            to=to_number
        )
        logger.info(f"WhatsApp message sent to {to_number}. SID: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}", exc_info=True)
        return False
