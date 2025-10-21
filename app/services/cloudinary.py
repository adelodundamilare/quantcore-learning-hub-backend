from app.core.config import settings
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

class CloudinaryService:

    def upload_image(self, file: bytes):
        result = cloudinary.uploader.upload(file, resource_type="image")
        return result["secure_url"]

    def upload_video(self, file: bytes):
        result = cloudinary.uploader.upload(file, resource_type="video")
        return result["secure_url"]

    def upload_pdf(self, file: bytes):
        result = cloudinary.uploader.upload(file, resource_type="raw", format="pdf")
        return result["secure_url"]

