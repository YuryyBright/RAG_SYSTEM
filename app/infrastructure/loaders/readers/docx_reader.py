# -*- coding: utf-8 -*-
"""Reader for Microsoft Word (.docx) files."""

from pathlib import Path
from .base_reader import BaseReader
from docx import Document


class DocxReader(BaseReader):
    """Reader for Microsoft Word (.docx) files."""

    def read(self, path: Path) -> str:
        """
        Read and extract text content from a .docx file.

        Parameters
        ----------
        path : Path
            Path to the .docx file.

        Returns
        -------
        str
            Extracted text content from the .docx file.
        """
    def read(self, path: Path) -> str:  
        try:
            doc = Document(path)
            return "\n".join(
                paragraph.text for section in doc.sections
                for paragraph in section.body.paragraphs
            )
        except Exception as e:
            return f"Error reading DOCX file: {str(e)}"

