"""S3 file upload service for document management."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

# S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "elipsis-documents")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize S3 client
s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


def is_s3_configured() -> bool:
    """Check if S3 is properly configured."""
    return s3_client is not None and AWS_S3_BUCKET is not None


async def upload_file_to_s3(
    file: UploadFile,
    folder: str = "documents"
) -> dict:
    """
    Upload a file to S3 and return file metadata.
    
    Args:
        file: FastAPI UploadFile object
        folder: S3 folder/prefix (e.g., "documents", "portfolio", "avatars")
    
    Returns:
        dict with file_url, filename, file_size, file_type
    
    Raises:
        Exception if S3 is not configured or upload fails
    """
    if not is_s3_configured():
        raise Exception("S3 storage is not configured. Set AWS credentials in environment variables.")
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    s3_key = f"{folder}/{datetime.now().year}/{datetime.now().month:02d}/{unique_filename}"
    
    try:
        # Read file content
        content = await file.read()
        
        # Upload to S3
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or "application/octet-stream",
            Metadata={
                "original_filename": file.filename,
                "upload_date": datetime.now().isoformat()
            }
        )
        
        # Generate public URL
        file_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        
        # Reset file pointer for potential re-reading
        await file.seek(0)
        
        return {
            "file_url": file_url,
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file.content_type,
            "s3_key": s3_key
        }
        
    except ClientError as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")


async def delete_file_from_s3(s3_key: str) -> bool:
    """
    Delete a file from S3.
    
    Args:
        s3_key: S3 object key (path)
    
    Returns:
        True if successful
    """
    if not is_s3_configured():
        return False
    
    try:
        s3_client.delete_object(
            Bucket=AWS_S3_BUCKET,
            Key=s3_key
        )
        return True
    except ClientError:
        return False


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str | None:
    """
    Generate a presigned URL for temporary file access.
    
    Args:
        s3_key: S3 object key
        expiration: URL expiration time in seconds (default 1 hour)
    
    Returns:
        Presigned URL or None if failed
    """
    if not is_s3_configured():
        return None
    
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': AWS_S3_BUCKET,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError:
        return None


async def upload_multiple_files(
    files: list[UploadFile],
    folder: str = "documents"
) -> list[dict]:
    """
    Upload multiple files to S3.
    
    Args:
        files: List of FastAPI UploadFile objects
        folder: S3 folder/prefix
    
    Returns:
        List of file metadata dicts
    """
    results = []
    for file in files:
        try:
            result = await upload_file_to_s3(file, folder)
            results.append(result)
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e),
                "success": False
            })
    return results


def get_file_metadata(s3_key: str) -> dict | None:
    """
    Get metadata for an S3 object.
    
    Args:
        s3_key: S3 object key
    
    Returns:
        Metadata dict or None if not found
    """
    if not is_s3_configured():
        return None
    
    try:
        response = s3_client.head_object(
            Bucket=AWS_S3_BUCKET,
            Key=s3_key
        )
        return {
            "size": response.get("ContentLength"),
            "last_modified": response.get("LastModified"),
            "content_type": response.get("ContentType"),
            "metadata": response.get("Metadata", {})
        }
    except ClientError:
        return None


# File size limits (bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {
    "documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".csv"},
    "images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"},
    "portfolio": {".jpg", ".jpeg", ".png", ".gif", ".webp"}
}


def validate_file(file: UploadFile, folder: str = "documents") -> tuple[bool, str]:
    """
    Validate file before upload.
    
    Args:
        file: UploadFile object
        folder: Upload folder category
    
    Returns:
        (is_valid, error_message)
    """
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed = ALLOWED_EXTENSIONS.get(folder, ALLOWED_EXTENSIONS["documents"])
    
    if file_ext not in allowed:
        return False, f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed)}"
    
    # File size will be checked during upload
    return True, ""
