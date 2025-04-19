# app/infrastructure/loaders/readers/base_reader.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

from charset_normalizer import from_path

from utils.logger_util import get_logger

logger = get_logger(__name__)

class BaseReader(ABC):
    """
    Abstract base class for file readers.

    All file readers should inherit from this class and implement the read method.
    """

    @abstractmethod
    def read(self, path: Path) -> str:
        """
        Read and process a file, returning its text content.

        Parameters
        ----------
        path : Path
            Path to the file to be read.

        Returns
        -------
        str
            Extracted text content from the file.

        Raises
        ------
        Exception
            If there's an error reading or processing the file.
        """
        pass

    def get_metadata(self, path: Path) -> Dict[str, Any]:
        """
        Extract metadata from a file.

        Parameters
        ----------
        path : Path
            Path to the file.

        Returns
        -------
        Dict[str, Any]
            Metadata extracted from the file.
        """
        # Default implementation returns basic file metadata
        return {
            "extension": path.suffix,
            "file_size": path.stat().st_size if path.exists() else 0,
        }

    def safe_read_text(self, path: Path) -> str:
        """Safely read text from file with encoding detection."""
        try:
            result = from_path(path)
            if result:
                best = result.best()
                if best and best.encoding:
                    encoding = best.encoding
                    return path.read_text(encoding=encoding, errors="replace")
            # Fallback to utf-8 if detection fails
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return ""

