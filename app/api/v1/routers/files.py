# app/api/routes/files.py
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from api.middleware_auth import get_current_active_user
from app.infrastructure.database.repository import get_async_db
from app.infrastructure.database.db_models import User, File as FileModel
from app.adapters.storage.file_manager import FileManager
from app.api.schemas.files import FileResponse as FileResponseSchema
from api.schemas.files import (
    FileProcessingRequest,
    FileProcessingResponse,
    FileProcessingReport,
    ProcessedFileSummary,
    FileProcessingRecommendations
)
from app.core.use_cases.file_processing import FileProcessingUseCase
from app.api.dependencies import file_processing_use_case


router = APIRouter()
file_manager = FileManager()


# @router.post("/", response_model=FileProcessingResponse)
# async def process_files(
#         request: FileProcessingRequest,
#         file_processing_use_case: FileProcessingUseCase = Depends(file_processing_use_case)
# ):
#     """
#     Process files in a directory for the RAG system.
#
#     This endpoint:
#     1. Reads different types of files
#     2. Detects language
#     3. Prepares text for the vector database
#     4. Provides a detailed report of processing results
#     """
#     try:
#         documents, report = await file_processing_use_case.process_directory(
#             request.directory_path,
#             recursive=request.recursive,
#             metadata=request.additional_metadata
#         )
#
#         return FileProcessingResponse(
#             success=True,
#             message=f"Successfully processed {len(documents)} documents",
#             documents_count=len(documents),
#             report=FileProcessingReport(
#                 summary=ProcessedFileSummary(**report["summary"]),
#                 details=report["details"],
#                 recommendations=FileProcessingRecommendations(**report["recommendations"])
#             )
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
@router.post("/", response_model=FileResponseSchema)
async def upload_file(
    theme_id: str = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_async_db)
):
    """
    Upload a file to the server.
    """
    try:
        # Define a safe destination folder
        upload_dir = Path("uploads") / str(current_user.id) / (theme_id or "unclassified")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_ext = Path(file.filename).suffix
        file_id = str(uuid4())
        file_path = upload_dir / f"{file_id}{file_ext}"

        # Save file
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Save to DB
        new_file = FileModel(
            id=file_id,
            filename=file.filename,
            file_path=str(file_path),
            content_type=file.content_type,
            is_public=False,
            owner_id=current_user.id,
            theme_id=theme_id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        return new_file

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
@router.post("/process", response_model=FileProcessingResponse)
async def process_files(
        request: FileProcessingRequest,
        current_user: User = Depends(get_current_active_user),
        file_processing_use_case_: FileProcessingUseCase = Depends(file_processing_use_case),
        db: Session = Depends(get_async_db)
):
    """
    Process files in a directory for the RAG system.

    This endpoint:
    1. Reads different types of files (marking unreadable files as warnings)
    2. Detects language (marking detection failures as warnings)
    3. Prepares text for vector database storage
    4. Provides a detailed report with recommendations for files with warnings
    """
    try:
        # Process the directory
        documents, report = await file_processing_use_case_.process_directory(
            request.directory_path,
            recursive=request.recursive,
            metadata=request.additional_metadata
        )

        # Analyze document quality
        quality_analysis = await file_processing_use_case_.analyze_document_quality(documents)

        # Add quality analysis to the report
        report["quality_analysis"] = quality_analysis

        # Create the response
        return FileProcessingResponse(
            success=True,
            message=f"Successfully processed {len(documents)} documents from {request.directory_path}",
            documents_count=len(documents),
            report=FileProcessingReport(
                summary=ProcessedFileSummary(
                    total_files=report["summary"]["total_files"],
                    successful=report["summary"]["successful"],
                    unreadable=report["summary"]["unreadable"],
                    language_detection_failures=report["summary"]["language_detection_failures"],
                    files_with_warnings=report["summary"]["files_with_warnings"]
                ),
                details=report["details"],
                recommendations=FileProcessingRecommendations(
                    files_to_review=report["recommendations"]["files_to_review"],
                    files_to_consider_removing=report["recommendations"]["files_to_consider_removing"]
                )
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during file processing: {str(e)}")
@router.get("/", response_model=List[FileResponseSchema])
async def list_files(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_async_db)
):
    """List user's files."""
    files = db.query(FileModel).filter(FileModel.owner_id == current_user.id).all()
    return files


@router.get("/{file_id}")
async def get_file(
        file_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_async_db)
):
    """Get a file."""
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if user has access to file
    if not file.is_public and file.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Return file
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type=file.content_type
    )


@router.delete("/{file_id}")
async def delete_file(
        file_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_async_db)
):
    """Delete a file."""
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if user owns the file
    if file.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete file from disk
    deleted = await file_manager.delete_file(file.file_path)

    # Delete file from database
    db.delete(file)
    db.commit()

    return {"detail": "File deleted successfully"}


@router.get("/public/{file_id}")
async def get_public_file(
        file_id: str,
        db: Session = Depends(get_async_db)
):
    """Get a public file without authentication."""
    # Get file from database
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.is_public == True).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found or not public")

    # Return file
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type=file.content_type
    )



@router.get("/supported-formats")
async def get_supported_formats(
        current_user: User = Depends(get_current_active_user),
        file_processing_use_case_: FileProcessingUseCase = Depends(file_processing_use_case)
):
    """
    Get the list of supported file formats for processing.
    """
    supported_extensions = file_processing_use_case_.file_processor.supported_extensions
    return {
        "supported_formats": supported_extensions,
        "count": len(supported_extensions)
    }