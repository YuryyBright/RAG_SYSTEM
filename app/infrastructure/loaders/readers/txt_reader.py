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
            return self.safe_read_text(path)
        except Exception as e:
            return f"Error reading text file: {str(e)}"