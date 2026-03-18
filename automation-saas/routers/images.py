import os
import shutil
import uuid
from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from db.models import ImageLibrary
from db.session import get_db
from core.security import get_current_user
from utils.config import settings

router = APIRouter(prefix="/images", tags=["Images"])

@router.post("")
async def upload_image(
    file: UploadFile = File(...),
    tag: str = Form(...),
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_user)
):
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join("uploads", filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    if settings.HTML.lower() == "true":
        # Also copy to static/uploads for UI serving if HTML UI is enabled
        file_path_ui = os.path.join("static/uploads", filename)
        if os.path.exists("static/uploads"):
            shutil.copyfile(file_path, file_path_ui)
        
    img = ImageLibrary(filename=filename, tag=tag)
    db.add(img)
    db.commit()
    return {"status": "ok", "filename": filename}
