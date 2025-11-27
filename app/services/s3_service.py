from app.core.config import settings
import boto3
from botocore.exceptions import ClientError
import uuid
import mimetypes
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

def parse_size_to_bytes(size_str: str) -> int:
    size_str = size_str.upper()
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    elif size_str.endswith('TB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024 * 1024
    else:
        return int(size_str)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
        self.bucket_name = settings.S3_BUCKET_NAME
        self.max_single_upload_size = parse_size_to_bytes(settings.MAX_SINGLE_UPLOAD_SIZE)
        self.chunk_size = parse_size_to_bytes(settings.CHUNK_SIZE)
        self.upload_progress = {}
        self.progress_ttl_hours = 24

    def upload_image(self, file: bytes, filename: Optional[str] = None) -> str:
        if not filename:
            filename = f"images/{uuid.uuid4().hex}"

        content_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=file,
                ContentType=content_type,
                ACL='public-read'
            )
            return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
        except ClientError as e:
            raise Exception(f"Failed to upload image: {str(e)}")

    def upload_pdf(self, file: bytes, filename: Optional[str] = None) -> str:
        if not filename:
            filename = f"documents/{uuid.uuid4().hex}.pdf"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=file,
                ContentType='application/pdf',
                ACL='public-read'
            )
            return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
        except ClientError as e:
            raise Exception(f"Failed to upload PDF: {str(e)}")

    def upload_video(self, file: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
        if not filename:
            filename = f"videos/{uuid.uuid4().hex}"

        validation_result = self.validate_video_file(file, filename)
        if not validation_result['valid']:
            raise Exception(validation_result['error'])

        if len(file) <= self.max_single_upload_size:
            url = self._upload_small_video(file, filename)
            return {
                "upload_id": None,
                "url": url,
                "message": "Video uploaded successfully"
            }
        else:
            upload_id = str(uuid.uuid4())
            self._upload_large_video(file, filename, upload_id)
            return {
                "upload_id": upload_id,
                "url": None,
                "message": "Video upload initiated"
            }

    def _upload_small_video(self, file: bytes, filename: str) -> str:
        content_type = mimetypes.guess_type(filename)[0] or 'video/mp4'

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=file,
                ContentType=content_type,
                ACL='public-read'
            )
            return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
        except ClientError as e:
            raise Exception(f"Failed to upload video: {str(e)}")

    def _upload_large_video(self, file: bytes, filename: str, upload_id: str):
        multipart_upload = None
        try:
            multipart_upload = self.s3_client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=filename,
                ContentType='video/mp4',
                ACL='public-read'
            )

            parts = []
            part_number = 1
            bytes_uploaded = 0

            for i in range(0, len(file), self.chunk_size):
                chunk = file[i:i + self.chunk_size]

                part_upload = self.s3_client.upload_part(
                    Bucket=self.bucket_name,
                    Key=filename,
                    PartNumber=part_number,
                    UploadId=multipart_upload['UploadId'],
                    Body=chunk
                )

                parts.append({
                    'ETag': part_upload['ETag'],
                    'PartNumber': part_number
                })

                bytes_uploaded += len(chunk)
                self._update_progress(upload_id, len(file), bytes_uploaded, filename)
                part_number += 1

            self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=filename,
                UploadId=multipart_upload['UploadId'],
                MultipartUpload={'Parts': parts}
            )

            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
            self._update_progress(upload_id, len(file), len(file), filename, url)

        except ClientError as e:
            if multipart_upload:
                try:
                    self.s3_client.abort_multipart_upload(
                        Bucket=self.bucket_name,
                        Key=filename,
                        UploadId=multipart_upload['UploadId']
                    )
                except:
                    pass
            raise Exception(f"Failed to upload video: {str(e)}")

    def _cleanup_old_progress(self):
        now = datetime.utcnow()
        expired_ids = [
            upload_id for upload_id, data in self.upload_progress.items()
            if now - data.get('created_at', now) > timedelta(hours=self.progress_ttl_hours)
        ]
        for upload_id in expired_ids:
            del self.upload_progress[upload_id]

    def _update_progress(self, upload_id: str, total_size: int, uploaded_size: int, filename: str, url: Optional[str] = None):
        self._cleanup_old_progress()
        
        progress_data = {
            'total_size': total_size,
            'uploaded_size': uploaded_size,
            'progress_percent': round((uploaded_size / total_size) * 100, 2),
            'filename': filename,
            'created_at': datetime.utcnow()
        }

        if url:
            progress_data['url'] = url

        self.upload_progress[upload_id] = progress_data

    def get_upload_progress(self, upload_id: str) -> Dict[str, Any]:
        self._cleanup_old_progress()
        
        progress = self.upload_progress.get(upload_id, {'progress_percent': 0})
        if progress.get('progress_percent') == 100 and 'url' not in progress:
            progress['url'] = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{progress.get('filename')}"
        return progress

    def validate_video_file(self, file: bytes, filename: str) -> Dict[str, Any]:
        file_size = len(file)
        file_extension = filename.split('.')[-1].lower() if '.' in filename else ''

        allowed_formats = [fmt.strip() for fmt in settings.ALLOWED_VIDEO_FORMATS.split(',')]
        max_size = parse_size_to_bytes(settings.MAX_VIDEO_SIZE)

        if file_extension not in allowed_formats:
            return {
                'valid': False,
                'error': f'Unsupported video format: {file_extension}. Allowed formats: {", ".join(allowed_formats)}'
            }

        if file_size > max_size:
            return {
                'valid': False,
                'error': f'File size ({file_size / 1024 / 1024 / 1024:.2f}GB) exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE})'
            }

        return {
            'valid': True,
            'file_size': file_size,
            'file_extension': file_extension
        }
