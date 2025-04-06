# app/files/file_manager.py
import os
import shutil
import uuid
from typing import Optional, BinaryIO
from fastapi import UploadFile
from app.config import settings

class FileManager:
    """Manager for storing and retrieving files on disk."""

    def __init__(self, base_path: str = settings.FILE_STORAGE_PATH):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    async def save_file(self, file: UploadFile, user_id: str) -> tuple:
        """
        Save file to disk.

        Args:
            file: The file to save
            user_id: The ID of the user who owns the file

        Returns:
            Tuple of (filename, file_path, file_size)
        """
        # Create user directory if it doesn't exist
        user_dir = os.path.join(self.base_path, user_id)
        os.makedirs(user_dir, exist_ok=True)

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        filename = f"{file_id}{file_ext}"

        # Define file path
        file_path = os.path.join(user_dir, filename)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Return file info
        return file.filename, file_path, file_size

    async def get_file(self, file_path: str) -> Optional[BinaryIO]:
        """
        Get file from disk.

        Args:
            file_path: Path to the file

        Returns:
            File handle or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None

        return open(file_path, "rb")

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from disk.

        Args:
            file_path: Path to the file

        Returns:
            True if file was deleted, False otherwise
        """
        if not os.path.exists(file_path):
            return False

        os.remove(file_path)
        return True