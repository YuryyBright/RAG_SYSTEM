# app/infrastructure/loaders/readers/base_reader.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


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