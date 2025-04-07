"""
Utility functions for handling various file operations in the RAG system.
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional, BinaryIO, Union
import uuid
import logging
import mimetypes

logger = logging.getLogger(__name__)

# Constants
ALLOWED_EXTENSIONS = {
    # Documents
    'pdf', 'docx', 'doc', 'txt', 'rtf', 'md', 'html', 'htm',
    # Data
    'csv', 'json', 'xml'
}
MAX_FILE_SIZE_MB = 50  # Maximum file size in MB


def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename."""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def is_allowed_file(filename: str) -> bool:
    """Check if the file has an allowed extension."""
    extension = get_file_extension(filename)
    return extension in ALLOWED_EXTENSIONS


def validate_file_size(file: BinaryIO, max_size_mb: int = MAX_FILE_SIZE_MB) -> bool:
    """
    Validate if the file size is within the acceptable limit.

    Args:
        file: File-like object
        max_size_mb: Maximum size in megabytes

    Returns:
        bool: True if file size is acceptable, False otherwise
    """
    # Get current position
    current_pos = file.tell()

    # Move to the end of the file
    file.seek(0, os.SEEK_END)

    # Get file size
    file_size = file.tell()

    # Reset file position
    file.seek(current_pos)

    # Convert MB to bytes (1 MB = 1,048,576 bytes)
    max_size_bytes = max_size_mb * 1024 * 1024

    return file_size <= max_size_bytes


def generate_safe_filename(original_filename: str) -> str:
    """
    Generate a unique, safe filename while preserving the original extension.

    Args:
        original_filename: Original filename provided by the user

    Returns:
        str: Safe, unique filename
    """
    extension = get_file_extension(original_filename)
    safe_name = f"{uuid.uuid4().hex}"

    if extension:
        safe_name = f"{safe_name}.{extension}"

    return safe_name


def save_uploaded_file(
        file: BinaryIO,
        filename: str,
        directory: Union[str, Path],
        preserve_filename: bool = False
) -> Path:
    """
    Save an uploaded file to the specified directory.

    Args:
        file: File object to save
        filename: Original filename
        directory: Target directory
        preserve_filename: Whether to preserve the original filename

    Returns:
        Path: Path to the saved file
    """
    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Generate safe filename or use the original
    safe_filename = filename if preserve_filename else generate_safe_filename(filename)

    # Create full path
    file_path = Path(directory) / safe_filename

    # Save the file
    with open(file_path, 'wb') as dest_file:
        # Reset position to beginning of file
        file.seek(0)
        shutil.copyfileobj(file, dest_file)

    logger.info(f"File saved to {file_path}")
    return file_path


def get_mime_type(file_path: Union[str, Path]) -> str:
    """
    Get the MIME type of a file.

    Args:
        file_path: Path to the file

    Returns:
        str: MIME type of the file
    """
    file_path = str(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def list_files(directory: Union[str, Path], extensions: Optional[List[str]] = None) -> List[Path]:
    """
    List all files in a directory with optional extension filtering.

    Args:
        directory: Directory to list files from
        extensions: List of extensions to filter by (without the dot)

    Returns:
        List[Path]: List of file paths
    """
    directory = Path(directory)

    if not directory.exists() or not directory.is_dir():
        logger.warning(f"Directory {directory} does not exist or is not a directory")
        return []

    files = [f for f in directory.iterdir() if f.is_file()]

    if extensions:
        files = [f for f in files if f.suffix.lower().lstrip('.') in extensions]

    return files


def copy_file(source: Union[str, Path], destination: Union[str, Path]) -> Path:
    """
    Copy a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        Path: Destination path
    """
    source = Path(source)
    destination = Path(destination)

    # Create parent directories if they don't exist
    os.makedirs(destination.parent, exist_ok=True)

    shutil.copy2(source, destination)
    logger.info(f"Copied {source} to {destination}")

    return destination


def remove_file(file_path: Union[str, Path]) -> bool:
    """
    Remove a file if it exists.

    Args:
        file_path: Path to the file to remove

    Returns:
        bool: True if file was removed, False otherwise
    """
    file_path = Path(file_path)

    if file_path.exists() and file_path.is_file():
        file_path.unlink()
        logger.info(f"Removed file {file_path}")
        return True

    logger.warning(f"File {file_path} does not exist or is not a file")
    return False