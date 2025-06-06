# app/api/routes/files.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import List, Optional, Union
import os

from api.dependencies.infrastructure_dependencies import get_task_manager
from api.middleware_auth import get_current_active_user
from api.schemas.task import TaskTypeEnum
from infrastructure.repositories import get_async_db
from app.infrastructure.database.db_models import User, File as FileModel
from app.modules.storage.file_manager import FileManager
from app.api.schemas.files import FileResponse as FileResponseSchema
from api.schemas.files import (
    FileProcessingRequest,
    FileProcessingResponse,
    FileProcessingReport,
    ProcessedFileSummary,
    FileProcessingRecommendations
)
from app.core.use_cases.file_processing import FileProcessingUseCase
from app.api.dependencies.use_case_dependencies import file_processing_use_case
from config import settings
from application.services.task_services import TaskManager
from infrastructure.repositories.file_repository import FileRepository

router = APIRouter()
file_manager = FileManager()

@router.post("/", response_model=List[FileResponseSchema])
async def upload_files(
        theme_id: Optional[str] = Form(None),
        files: Union[UploadFile, List[UploadFile]] = File(...),
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Upload one or multiple files and store metadata in the database.
    """
    repo = FileRepository(db)
    saved_files = []

    # Normalize single file to list
    if isinstance(files, UploadFile):
        files = [files]

    try:
        for file in files:
            # Save file using FileManager
            filename, path, size = await file_manager.save_file_to_theme(file, str(current_user.id), theme_id)

            # Store file record in DB
            file_record = await repo.create_file(
                filename=file.filename,
                file_path=str(path),
                content_type=file.content_type,
                size=size,
                is_public=False,
                owner_id=current_user.id,
                theme_id=theme_id
            )
            saved_files.append(file_record)
            # Associate with theme (many-to-many relationship)
            if theme_id:
                await repo.link_file_to_theme(file_record.id, theme_id)
        return saved_files

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/process", response_model=FileProcessingResponse)
async def process_files_with_chunking(
        request: FileProcessingRequest,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_async_db),
        file_processing_use_case_: FileProcessingUseCase = Depends(file_processing_use_case),
        task_service: TaskManager = Depends(get_task_manager)
):
    """
    Read files from `directory_path`, chunk them, save to the document store,
    and create embeddings in the vector index. Returns a detailed report.
    Steps:
      1. Read and chunk files
      2. Save each chunk to the document store
      3. Embed chunks and store vectors
      4. Return a summary report with detailed logs
    """
    user_theme_path = settings.UPLOAD_DIR / str(current_user.id) / request.theme_id
    if not user_theme_path.exists() or not user_theme_path.is_dir():
        raise HTTPException(status_code=404, detail="Theme directory does not exist.")

    # Create a task to track progress
    task = await task_service.create_task(
        user_id=current_user.id,
        theme_id=request.theme_id,
        task_type=TaskTypeEnum.THEME_PROCESSING,
        description=f"Processing theme: {request.theme_id}",
        metadata={
            "step": "processing",
            "files_count": len(list(user_theme_path.glob('*'))),
            "chunk_size": request.chunk_size,
            "chunk_overlap": request.chunk_overlap
        }
    )

    try:
        # Update task status to in_progress
        await task_service.update_task_status(task.id, "in_progress", current_step=0)

        # Call our integrated process
        report = await file_processing_use_case_.process_and_vectorize_directory(
            directory_path=str(user_theme_path),
            recursive=request.recursive,
            metadata=request.additional_metadata or {},
            theme_id=request.theme_id,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            task_id=task.id,  # Pass task_id to enable progress updates
            user_id = current_user.id,
        )

        # Mark task as completed
        await task_service.update_task_status(task.id, "completed", current_step=3, progress=100)

        # Construct the response schema
        summary = report["summary"]
        return FileProcessingResponse(
            success=True,
            task_id=task.id,
            message=(
                f"Successfully processed {summary['successful_files']} files, "
                f"created {summary['total_chunks_created']} chunks, "
                f"vectorized {summary['chunks_vectorized']} chunks."
            ),
            documents_count=summary["successful_files"],
            report=FileProcessingReport(
                summary=ProcessedFileSummary(
                    total_files=summary["total_files"],
                    successful=summary["successful_files"],
                    unreadable=summary["unreadable_files"],
                    language_detection_failures=summary["language_detection_failures"],
                    files_with_warnings=summary["files_with_warnings"],
                    total_chunks_created=summary["total_chunks_created"],
                    chunks_vectorized=summary["chunks_vectorized"]
                ),
                details=report["details"],
                recommendations=FileProcessingRecommendations(
                    files_to_review=report["recommendations"]["files_to_review"],
                    files_to_consider_removing=report["recommendations"]["files_to_consider_removing"]
                )
            )
        )
    except ValueError as e:
        # Update task as failed
        await task_service.update_task_status(task.id, "failed", error_message=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Update task as failed with error details
        await task_service.update_task_status(task.id, "failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred during file processing: {str(e)}")



@router.post("/vectorize", response_model=FileProcessingResponse)
async def vectorize_files(
        theme_id: str,
        batch_size: int = 100,
        current_user: User = Depends(get_current_active_user),
        file_processing_use_case_: FileProcessingUseCase = Depends(file_processing_use_case),
        db: Session = Depends(get_async_db)
):
    """
    Generate embeddings and store in vector database for a given theme.

    This endpoint:
    1. Gets all processed files for a theme
    2. Generates embeddings in batches
    3. Stores the embeddings in the vector database
    4. Provides a detailed report of the process
    """
    try:
        # Verify theme exists and user has access
        repo = FileRepository(db)
        theme_files = await repo.get_files_by_theme_id(theme_id, current_user.id)

        if not theme_files:
            raise HTTPException(status_code=404, detail=f"No files found for theme ID: {theme_id}")

        # Get document content from files
        file_paths = [file.file_path for file in theme_files]

        # Generate embeddings and store in vector DB
        embedding_results, vectorization_report = await file_processing_use_case_.vectorize_files(
            file_paths=file_paths,
            theme_id=theme_id,
            batch_size=batch_size
        )

        # Create the response
        return FileProcessingResponse(
            success=True,
            message=f"Successfully vectorized {len(embedding_results)} documents for theme {theme_id}",
            documents_count=len(embedding_results),
            report=FileProcessingReport(
                summary=ProcessedFileSummary(
                    total_files=vectorization_report["summary"]["total_files"],
                    successful=vectorization_report["summary"]["successful"],
                    unreadable=vectorization_report["summary"]["unreadable"],
                    language_detection_failures=vectorization_report["summary"]["language_detection_failures"],
                    files_with_warnings=vectorization_report["summary"]["files_with_warnings"]
                ),
                details=vectorization_report["details"],
                recommendations=FileProcessingRecommendations(
                    files_to_review=vectorization_report["recommendations"]["files_to_review"],
                    files_to_consider_removing=vectorization_report["recommendations"]["files_to_consider_removing"]
                )
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during vectorization: {str(e)}")


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
        db: AsyncSession = Depends(get_async_db)
):
    """Delete a file using FileRepository and FileManager."""
    repo = FileRepository(db)

    # Fetch file
    file = await repo.get_file_by_id(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Authorization check
    if file.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Delete file from disk
        await file_manager.delete_file(file.file_path)

        # Delete file from DB
        await repo.delete_file(file.id)

        return {"detail": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


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


@router.get("/theme/{theme_id}/vector-status")
async def get_vectorization_status(
        theme_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_async_db),
        file_processing_use_case_: FileProcessingUseCase = Depends(file_processing_use_case)
):
    """
    Get the vectorization status for a theme.
    """
    try:
        status = await file_processing_use_case_.get_vectorization_status(theme_id)
        return {
            "theme_id": theme_id,
            "total_files": status["total_files"],
            "vectorized_files": status["vectorized_files"],
            "percent_complete": status["percent_complete"],
            "status": status["status"],
            "vector_db_info": status["vector_db_info"],
            "last_updated": status["last_updated"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get vectorization status: {str(e)}")