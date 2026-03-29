"""
Seed script — upload AI-generated assets to Cloudinary and populate the ImageLibrary database.
"""

import sys
import os
import cloudinary
import cloudinary.uploader
from sqlalchemy.orm import Session

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from db.models import ImageLibrary
from utils.config import settings

def seed_image(local_path: str, tag: str, description: str):
    """Upload an image to Cloudinary and save to DB."""
    if not os.path.exists(local_path):
        print(f"File not found: {local_path}")
        return

    # Use cloudname provided: dtq5yhujj (should be in CLOUDINARY_URL in .env)
    if not settings.CLOUDINARY_URL:
        print("CLOUDINARY_URL not set in .env. Skipping upload.")
        return

    # Manually parse cloudinary://api_key:api_secret@cloud_name
    conn_str = settings.CLOUDINARY_URL.replace("cloudinary://", "")
    creds, cloud_name = conn_str.split("@")
    api_key, api_secret = creds.split(":")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )

    db = SessionLocal()
    try:
        print(f"Uploading {local_path} to Cloudinary...")
        upload_result = cloudinary.uploader.upload(
            local_path,
            folder="automation_saas/assets",
            overwrite=True
        )
        
        url = upload_result.get("secure_url")
        filename = os.path.basename(local_path)
        
        # Save to DB
        img = ImageLibrary(
            filename=filename,
            tag=tag,
            description=description,
            cloudinary_url=url,
            platform_bias="both"
        )
        
        db.add(img)
        db.commit()
        print(f"Successfully seeded: {filename} -> {url}")
        
    except Exception as e:
        print(f"Failed to seed {local_path}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Seed the first generated image
    FIRST_IMAGE_PATH = r"C:\Users\hi\.gemini\antigravity\brain\8eb9ed0c-a88d-47a4-bffa-9fab841bf1c4\saas_dashboard_ui_1_1774786872383.png"
    
    seed_image(
        FIRST_IMAGE_PATH,
        tag="ui",
        description="A sleek, modern SaaS dashboard with purple and dark blue gradients, showing professional charts and analytics. Glassmorphism style."
    )
