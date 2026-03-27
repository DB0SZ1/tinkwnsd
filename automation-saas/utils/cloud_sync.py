"""
Syncs the ephemeral SQLite database to Cloudinary as JSON, enabling persistence across Render deployments/sleeps.
"""

import json
import logging
import httpx
import cloudinary
import cloudinary.uploader
from datetime import datetime
from uuid import UUID

from db.session import SessionLocal
from db.models import Topic, Post, PostMetric, Lead, ImageLibrary
from utils.config import settings
from sqlalchemy.orm import class_mapper

logger = logging.getLogger(__name__)

if settings.CLOUDINARY_URL:
    cloudinary.config(url=settings.CLOUDINARY_URL)

def serialize_model(obj):
    """Serialize a SQLAlchemy model to dict."""
    data = {}
    for column in class_mapper(obj.__class__).columns:
        val = getattr(obj, column.key)
        if isinstance(val, datetime):
            data[column.key] = val.isoformat()
        elif isinstance(val, UUID):
            data[column.key] = val.hex
        else:
            data[column.key] = val
    return data

def backup_db_to_cloudinary():
    if not settings.CLOUDINARY_URL:
        logger.warning("CLOUDINARY_URL not set. Skipping DB JSON backup.")
        return

    db = SessionLocal()
    try:
        data = {
            "topics": [serialize_model(t) for t in db.query(Topic).all()],
            "posts": [serialize_model(p) for p in db.query(Post).all()],
            "post_metrics": [serialize_model(pm) for pm in db.query(PostMetric).all()],
            "leads": [serialize_model(l) for l in db.query(Lead).all()],
            "image_library": [serialize_model(i) for i in db.query(ImageLibrary).all()],
        }

        with open("backup.json", "w") as f:
            json.dump(data, f)
            
        logger.info("Uploading database backup to Cloudinary...")
        res = cloudinary.uploader.upload(
            "backup.json",
            resource_type="raw",
            public_id="saas_db_backup.json",
            overwrite=True
        )
        logger.info(f"Database backup to Cloudinary successful: {res.get('secure_url')}")
    except Exception as e:
        logger.error(f"Cloudinary DB backup failed: {e}", exc_info=True)
    finally:
        db.close()

def restore_db_from_cloudinary():
    if not settings.CLOUDINARY_URL:
        logger.warning("CLOUDINARY_URL not set. Skipping DB restore.")
        return
        
    db = SessionLocal()
    try:
        url = cloudinary.CloudinaryImage("saas_db_backup.json").build_url(resource_type="raw")
        logger.info(f"Checking for JSON DB backup at {url}")
        res = httpx.get(url, timeout=10.0)
        
        if res.status_code != 200:
            logger.info("No remote DB backup found or HTTP error. Starting fresh SQLite DB.")
            return
            
        data = res.json()
        logger.info("Found DB backup JSON on Cloudinary. Injecting into SQLite...")
        
        models_map = {
            "topics": Topic,
            "posts": Post,
            "post_metrics": PostMetric,
            "leads": Lead,
            "image_library": ImageLibrary,
        }
        
        for key, model_class in models_map.items():
            records = data.get(key, [])
            for r in records:
                # Convert ISO string dates and UUIDs back
                for k, v in r.items():
                    if isinstance(v, str) and "T" in v and (v.endswith("Z") or "+" in v or "-" in v):
                        try:
                            # Handle python fromisoformat
                            clean_v = v.replace("Z", "+00:00")
                            r[k] = datetime.fromisoformat(clean_v)
                        except ValueError:
                            pass
                    elif isinstance(v, str) and len(v) == 32 and model_class in [Post, PostMetric, Lead] and k in ["id", "post_id"]:
                        r[k] = UUID(v)

                obj = db.query(model_class).filter_by(id=r["id"]).first()
                if not obj:
                    db.add(model_class(**r))
                else:
                    for k, v in r.items():
                        setattr(obj, k, v)
        
        db.commit()
        logger.info("Cloudinary Database restore complete.")
    except Exception as e:
        logger.error(f"Cloudinary Database restore failed: {e}", exc_info=True)
    finally:
        db.close()

def keep_alive_ping():
    """Ping the public app URL to prevent Render from sleeping."""
    if not settings.PUBLIC_APP_URL:
        # Default fallback to localhost for logs sanity 
        target_url = "http://127.0.0.1:8080/health"
    else:
        target_url = f"{settings.PUBLIC_APP_URL}/health"
        
    try:
        res = httpx.get(target_url, timeout=5.0)
        logger.info(f"Keep-alive ping to {target_url} returned {res.status_code}")
    except Exception as e:
        logger.warning(f"Keep-alive ping to {target_url} failed: {e}")
