"""File upload API routes for documents and images."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.services_s3 import (
    upload_file_to_s3,
    upload_multiple_files,
    delete_file_from_s3,
    is_s3_configured,
    validate_file,
    MAX_FILE_SIZE
)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload/document")
async def upload_request_document(
    request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload a document for a physical assessment request.
    
    - **request_id**: Request ID
    - **file**: Document file (PDF, DOCX, XLSX, etc.)
    """
    if not is_s3_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File upload service is not configured"
        )
    
    # Validate file
    is_valid, error = validate_file(file, "documents")
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Get request and verify ownership
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Check if user owns the organization
    org = db.get(models.Organization, req.organization_id)
    if not org or (org.user_id != current_user.id and not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to upload documents for this request"
        )
    
    try:
        # Upload to S3
        file_data = await upload_file_to_s3(file, folder="documents")
        
        # Save to database
        document = models.RequestDocument(
            request_id=request_id,
            filename=file_data["filename"],
            file_url=file_data["file_url"],
            file_type=file_data["file_type"],
            file_size=file_data["file_size"]
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "id": document.id,
            "filename": document.filename,
            "file_url": document.file_url,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "uploaded_at": document.uploaded_at.isoformat(),
            "message": "Document uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.post("/upload/documents/batch")
async def upload_multiple_documents(
    request_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload multiple documents for a request at once.
    
    - **request_id**: Request ID
    - **files**: List of document files (max 10)
    """
    if not is_s3_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File upload service is not configured"
        )
    
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per upload"
        )
    
    # Get request and verify ownership
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    org = db.get(models.Organization, req.organization_id)
    if not org or (org.user_id != current_user.id and not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Validate all files first
    for file in files:
        is_valid, error = validate_file(file, "documents")
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{file.filename}: {error}"
            )
    
    # Upload files
    results = await upload_multiple_files(files, folder="documents")
    
    # Save successful uploads to database
    documents = []
    for file_data in results:
        if "error" not in file_data:
            document = models.RequestDocument(
                request_id=request_id,
                filename=file_data["filename"],
                file_url=file_data["file_url"],
                file_type=file_data["file_type"],
                file_size=file_data["file_size"]
            )
            db.add(document)
            documents.append(document)
    
    db.commit()
    
    return {
        "uploaded": len(documents),
        "failed": len(results) - len(documents),
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_url": doc.file_url
            }
            for doc in documents
        ]
    }


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a document."""
    document = db.get(models.RequestDocument, document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check permission
    req = db.get(models.PhysicalAssessmentRequest, document.request_id)
    if req:
        org = db.get(models.Organization, req.organization_id)
        if not org or (org.user_id != current_user.id and not current_user.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
    
    # Extract S3 key from URL
    if "s3.amazonaws.com" in document.file_url:
        s3_key = document.file_url.split(".amazonaws.com/")[1]
        delete_file_from_s3(s3_key)
    
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.post("/upload/portfolio")
async def upload_portfolio_image(
    project_name: str,
    description: str | None = None,
    project_url: str | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload a portfolio image (bidders only).
    
    - **project_name**: Project name
    - **description**: Project description
    - **project_url**: Live project URL
    - **file**: Image file (JPG, PNG, etc.)
    """
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidders can upload portfolio images"
        )
    
    if not is_s3_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File upload service is not configured"
        )
    
    # Validate file
    is_valid, error = validate_file(file, "portfolio")
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Get bidder company
    bidder = db.scalar(
        select(models.BidderCompany).where(
            models.BidderCompany.user_id == current_user.id
        )
    )
    
    if not bidder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please create your bidder profile first"
        )
    
    try:
        # Upload to S3
        file_data = await upload_file_to_s3(file, folder="portfolio")
        
        # Save to database
        portfolio = models.BidderPortfolio(
            bidder_company_id=bidder.id,
            project_name=project_name,
            description=description,
            image_url=file_data["file_url"],
            project_url=project_url
        )
        
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
        
        return {
            "id": portfolio.id,
            "project_name": portfolio.project_name,
            "image_url": portfolio.image_url,
            "message": "Portfolio image uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.get("/limits")
def get_upload_limits():
    """Get file upload limits and allowed types."""
    return {
        "max_file_size": MAX_FILE_SIZE,
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "allowed_documents": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".csv"],
        "allowed_images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "s3_configured": is_s3_configured()
    }
