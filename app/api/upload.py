from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import uuid
from typing import List

router = APIRouter()

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_extension = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "url": f"/static/uploads/{file_name}",
            "filename": file.filename,
            "content_type": file.content_type,
            "size": os.path.getsize(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
