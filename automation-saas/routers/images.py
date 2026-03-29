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
    file: UploadFile = File(None),
    tag: str = Form(...),
    description: str = Form(None),
    cloudinary_url: str = Form(None),
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_user)
):
    filename = None
    if file:
        filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        if settings.HTML.lower() == "true":
            file_path_ui = os.path.join("static/uploads", filename)
            os.makedirs("static/uploads", exist_ok=True)
            shutil.copyfile(file_path, file_path_ui)
    
    if not filename and not cloudinary_url:
        return {"status": "error", "message": "File or Cloudinary URL required"}

    img = ImageLibrary(
        filename=filename, 
        tag=tag, 
        description=description,
        cloudinary_url=cloudinary_url
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return {"status": "ok", "filename": filename, "id": img.id}
