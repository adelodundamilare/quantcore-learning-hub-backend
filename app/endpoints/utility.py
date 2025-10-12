
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.crud.user import user as user_crud
from app.schemas import user as user_schema
from app.utils.deps import get_current_user
from app.utils.logger import setup_logger
from app.models.user import User
from app.services.email import EmailService
from app.services.user import UserService
from app.services.cloudinary import CloudinaryService

logger = setup_logger("utility_api", "utility.log")

router = APIRouter()
user_service = UserService()
cloudinary_service = CloudinaryService()

@router.post("/upload-to-cloud")
async def upload_image(
    file: UploadFile = File(...)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
    try:
        file_bytes = await file.read()
        res = cloudinary_service.upload_image(file_bytes)
        return {"message": "Image uploaded successfully", "url": res}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

@router.post("/upload-video-to-cloud")
async def upload_video(
    file: UploadFile = File(...)
):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")
    try:
        file_bytes = await file.read()
        res = cloudinary_service.upload_video(file_bytes)
        return {"message": "Video uploaded successfully", "url": res}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise
