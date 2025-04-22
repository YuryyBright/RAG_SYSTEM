# app/modules/storage/file_manager.py
import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from typing import Tuple, Optional
from app.config import settings
from pathlib import Path

from utils.logger_util import get_logger

logger = get_logger(__name__)

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

    async def save_file_to_theme(
        self, file: UploadFile, user_id: str, theme_id: Optional[str]
    ) -> Tuple[str, str, int]:
        """
        Save a file under a user's theme directory.

        Parameters
        ----------
        file : UploadFile
            The file to save.
        user_id : str
            The ID of the uploading user.
        theme_id : Optional[str]
            The theme this file belongs to.

        Returns
        -------
        Tuple[str, str, int]
            (filename, full path, file size in bytes)
        """
        file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{file_extension}' not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        user_theme_dir = self.upload_dir / user_id / (theme_id or "unclassified")
        user_theme_dir.mkdir(parents=True, exist_ok=True)

        file_path = user_theme_dir / unique_filename

        # Determine file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Write file to disk
        try:
            with open(file_path, "wb") as out_file:
                shutil.copyfileobj(file.file, out_file)
            logger.info(f"File saved: {file_path}")
        except Exception as e:
            logger.exception(f"Failed to save file: {file.filename}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        return unique_filename, str(file_path), file_size

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from disk.

        Parameters
        ----------
        file_path : str
            Absolute file path.

        Returns
        -------
        bool
            True if file was deleted, False otherwise.
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"Deleted file from disk: {file_path}")
                return True
            logger.warning(f"Tried to delete non-existent file: {file_path}")
            return False
        except Exception as e:
            logger.exception(f"Failed to delete file at {file_path}")
            raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")