# app/adapters/storage/file_manager.py
import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from typing import Tuple
from app.config import settings
from pathlib import Path


class FileManager:
    """
    File manager for handling file uploads and deletions.
    """

    def __init__(self):
        """
        Initialize the file manager.

        Creates the upload directory if it doesn't exist.
        """
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_file(self, file: UploadFile, user_id: str) -> Tuple[str, str, int]:
        """
        Save an uploaded file to disk.

        Parameters
        ----------
        file : UploadFile
            The uploaded file.
        user_id : str
            The ID of the user uploading the file.

        Returns
        -------
        Tuple[str, str, int]
            The filename, file path, and file size.

        Raises
        ------
        HTTPException
            If the file extension is not allowed or the file size exceeds the limit.
        """
        # Validate file extension
        file_extension = file.filename.split(".")[-1] if "." in file.filename else ""
        if file_extension.lower() not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{file_extension}' not allowed. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Generate a unique filename
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"

        # Create user directory
        user_dir = os.path.join(self.upload_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(user_dir, unique_filename)

        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Seek back to start

        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size} bytes) exceeds the maximum allowed size ({settings.MAX_FILE_SIZE} bytes)"
            )

        # Write file to disk
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return unique_filename, file_path, file_size

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from disk.

        Parameters
        ----------
        file_path : str
            The path to the file to delete.

        Returns
        -------
        bool
            True if the file was deleted, False otherwise.
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                return True
            return False
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")