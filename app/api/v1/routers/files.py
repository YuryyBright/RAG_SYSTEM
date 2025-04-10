# app/api/routes/files.py
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

router = APIRouter()
file_manager = FileManager()


@router.post("/upload", response_model=FileResponseSchema)
async def upload_file(
        file: UploadFile = File(...),
        is_public: bool = False,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_async_db)
):
    """Upload a file."""
    # Save file to disk
    filename, file_path, file_size = await file_manager.save_file(file, current_user.id)

    # Create file record in database
    db_file = FileModel(
        filename=filename,
        file_path=file_path,
        content_type=file.content_type,
        size=file_size,
        is_public=is_public,
        owner_id=current_user.id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return db_file


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