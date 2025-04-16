# app/infrastructure/loaders/readers/txt_reader.py
from pathlib import Path

from .base_reader import BaseReader


class TxtReader(BaseReader):
    """Reader for plain text files (.txt, .md, etc.)."""

    def read(self, path: Path) -> str:
        """
        Read content from text files.

        Parameters
        ----------
        path : Path
            Path to the text file.

        Returns
        -------
        str
            Content of the text file.
        """
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading text file: {str(e)}"