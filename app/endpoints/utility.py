from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from app.core.database import get_db
from app.crud.user import user as user_crud
from app.schemas import user as user_schema
from app.schemas.utility import ContactAdminRequest
from app.utils.deps import get_current_user
from app.utils.logger import setup_logger
from app.models.user import User
from app.services.email import EmailService
from app.services.user import UserService
from app.services.s3_service import S3Service
from app.core.config import settings

logger = setup_logger("utility_api", "utility.log")

router = APIRouter()
user_service_instance = UserService()
s3_service = S3Service()

@router.post("/upload-to-cloud")
async def upload_file_to_cloud(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image or a PDF.")
    try:
        file_bytes = await file.read()
        if file.content_type.startswith("image/"):
            res = s3_service.upload_image(file_bytes, file.filename)
        elif file.content_type == "application/pdf":
            res = s3_service.upload_pdf(file_bytes, file.filename)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type.")
        logger.info(f"User {current_user.id} uploaded file: {file.filename}")
        return {"message": "File uploaded successfully", "url": res, "upload_id": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

@router.post("/upload-video-to-cloud")
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")

    try:
        file_bytes = await file.read()
        res = s3_service.upload_video(file_bytes, file.filename)
        logger.info(f"User {current_user.id} uploaded video: {file.filename}, upload_id: {res.get('upload_id')}")
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video upload error for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/upload-progress/{upload_id}")
async def get_upload_progress(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    try:
        progress = s3_service.get_upload_progress(upload_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Upload not found or expired")
        return {
            "upload_id": upload_id,
            "progress": progress
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload progress for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get upload progress")

@router.post("/contact-admin", response_model=dict)
async def contact_admin(
    contact_data: ContactAdminRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        await EmailService.send_email(
            to_email=settings.EMAILS_FROM_EMAIL,
            subject=f"Support Request: {contact_data.subject}",
            template_name="contact_admin.html",
            template_context={
                "user_name": current_user.full_name,
                "user_email": current_user.email,
                "user_role": getattr(current_user.role, 'name', 'Unknown') if hasattr(current_user, 'role') else 'Unknown',
                "user_school": getattr(current_user.school, 'name', 'Platform') if hasattr(current_user, 'school') and current_user.school else 'Platform',
                "subject": contact_data.subject,
                "message": contact_data.message,
                "screenshot_url": contact_data.screenshot_url
            }
        )

        logger.info(f"User {current_user.email} contacted administrators about: {contact_data.subject}")

        return {"message": "Message sent successfully to administrators"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending contact admin email: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send message to administrators")
