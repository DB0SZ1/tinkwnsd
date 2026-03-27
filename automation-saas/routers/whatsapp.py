from __future__ import annotations

import os
import uuid
import base64
import httpx
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from db.session import get_db
from db.models import Topic, ImageLibrary, WhatsAppState, PostMetric, Lead
from utils.logger import get_logger
from utils.config import settings
from utils.twilio_client import send_whatsapp_message

logger = get_logger(__name__)
router = APIRouter()

async def download_image(url: str, filename: str) -> str:
    async with httpx.AsyncClient() as client:
        # Provide basic auth in case Twilio requires it
        auth = None
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        resp = await client.get(url, auth=auth)
        resp.raise_for_status()
        filepath = os.path.join("uploads", filename)
        with open(filepath, "wb") as f:
            f.write(resp.content)
        return filepath

def get_base64_image(filepath: str) -> str:
    with open(filepath, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    ext = os.path.splitext(filepath)[1].lower().strip('.')
    if ext == 'jpg': ext = 'jpeg'
    return f"data:image/{ext};base64,{encoded}"

async def generate_topic_from_image(image_path: str, mood: str) -> str:
    prompt = f"Analyze this image and the user's requested context/mood: '{mood}'. Generate a short, engaging, single-sentence topic statement (max 10 words) that can be used as a seed for social media posts."
    b64_image = get_base64_image(image_path)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-flash-1.5",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": b64_image}}
                        ]
                    }
                ]
            }
        )
        resp.raise_for_status()
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip(' "\'')
        return f"Topic based on image ({mood})"

async def process_webhook_message(body: str, from_number: str, num_media: int, media_url: str, content_type: str, db: Session):
    try:
        # Retrieve or create state
        state = db.query(WhatsAppState).filter(WhatsAppState.user_phone == from_number).first()
        if not state:
            state = WhatsAppState(user_phone=from_number, state="idle")
            db.add(state)
            db.commit()

        body = body.strip()

        # Handle /metrics command
        if body.lower() == "/metrics":
            metrics = db.query(PostMetric).all()
            leads = db.query(Lead).count()
            likes = sum(m.likes for m in metrics)
            comments = sum(m.comments for m in metrics)
            reply = f"📊 *Quick Metrics*\n👍 Likes: {likes}\n💬 Comments: {comments}\n🎯 Leads: {leads}"
            send_whatsapp_message(from_number, reply)
            return
            
        # Handle /topic
        if body.lower().startswith("/topic"):
            topic_text = body[len("/topic"):].strip()
            if not topic_text:
                send_whatsapp_message(from_number, "Please provide the topic text! E.g. `/topic Future of AI`")
                return
                
            topic = Topic(topic=topic_text, platform="both", active=True)
            db.add(topic)
            reply = f"✅ Topic added: {topic_text}"
            
            # If media is attached to /topic
            if num_media > 0 and media_url:
                filename = f"wa_{uuid.uuid4().hex[:8]}.jpg"
                await download_image(media_url, filename)
                img = ImageLibrary(filename=filename, tag="personal", platform_bias="both")
                db.add(img)
                reply += "\n📸 Image also saved to library."
                
            db.commit()
            send_whatsapp_message(from_number, reply)
            return
            
        # Handle standalone image with no specific command
        if num_media > 0 and media_url:
            filename = f"wa_{uuid.uuid4().hex[:8]}.jpg"
            filepath = await download_image(media_url, filename)
            
            # If user typed something along with image but not /topic, treat it as mood
            mood = body if body else ""
            if mood:
                send_whatsapp_message(from_number, "Generating topic from your image and mood...")
                try:
                    gen_topic = await generate_topic_from_image(filepath, mood)
                    db.add(Topic(topic=gen_topic, platform="both", active=True))
                    db.add(ImageLibrary(filename=filename, tag="personal", platform_bias="both"))
                    db.commit()
                    send_whatsapp_message(from_number, f"✅ Generated & added topic: {gen_topic}")
                except Exception as e:
                    logger.error(f"Vision error: {e}")
                    send_whatsapp_message(from_number, "Failed to analyze image.")
            else:
                # Wait for mood
                state.state = "waiting_for_mood"
                state.temp_image_path = filename
                db.commit()
                send_whatsapp_message(from_number, "Got the image! 📸 What mood or context should I use for the topic? (e.g. 'motivational', 'funny startup fail')")
            return
            
        # Handle state-based replies
        if state.state == "waiting_for_mood" and state.temp_image_path:
            mood = body
            filepath = os.path.join("uploads", state.temp_image_path)
            if os.path.exists(filepath):
                send_whatsapp_message(from_number, f"Got the mood: '{mood}'. Generating topic...")
                try:
                    gen_topic = await generate_topic_from_image(filepath, mood)
                    db.add(Topic(topic=gen_topic, platform="both", active=True))
                    db.add(ImageLibrary(filename=state.temp_image_path, tag="personal", platform_bias="both"))
                    state.state = "idle"
                    state.temp_image_path = None
                    db.commit()
                    send_whatsapp_message(from_number, f"✅ Generated & added topic: {gen_topic}")
                except Exception as e:
                    logger.error(f"Vision generation failed: {e}")
                    send_whatsapp_message(from_number, "Failed to generate topic. Context reset.")
                    state.state = "idle"
                    state.temp_image_path = None
                    db.commit()
            else:
                send_whatsapp_message(from_number, "I lost the image somehow! Please upload it again.")
                state.state = "idle"
                db.commit()
            return

        # Fallback help
        help_text = (
            "🤖 *Automation Bot Commands*\n"
            "- `/topic [text]` : Add a new topic\n"
            "- `/metrics` : Get current stats\n"
            "- Send an image: I'll ask for a mood & generate a topic.\n"
        )
        send_whatsapp_message(from_number, help_text)
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)


@router.post("/webhook")
async def twilio_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    form_data = await request.form()
    from_number = form_data.get("From", "")
    body = form_data.get("Body", "")
    num_media = int(form_data.get("NumMedia", 0))
    media_url = form_data.get("MediaUrl0")
    content_type = form_data.get("MediaContentType0")

    # Security Check
    allowed = settings.USER_WHATSAPP_NUMBER
    if not allowed.startswith("whatsapp:"):
        allowed = f"whatsapp:{allowed}"
    
    if from_number != allowed and allowed.strip() != "whatsapp:":
        logger.warning(f"Unauthorized WhatsApp message from {from_number}")
        # Still return generic 200 so Twilio doesn't retry
        return Response(content="<Response></Response>", media_type="application/xml")

    # Twilio demands a fast response. We return empty TwiML and process async.
    background_tasks.add_task(
        process_webhook_message,
        body=body,
        from_number=from_number,
        num_media=num_media,
        media_url=media_url,
        content_type=content_type,
        db=db
    )
    
    return Response(content="<Response></Response>", media_type="application/xml")
