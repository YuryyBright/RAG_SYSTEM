# app/infrastructure/loaders/readers/pdf_reader.py
from pathlib import Path

from .base_reader import BaseReader


class PdfReader(BaseReader):
    """Reader for PDF files."""

    def read(self, path: Path) -> str:
        """
        Extract text from PDF files.

        Parameters
        ----------
        path : Path
            Path to the PDF file.

        Returns
        -------
        str
            Extracted text content from PDF.
        """
        try:
            from PyPDF2 import PdfReader as PyPDF2Reader
            reader = PyPDF2Reader(path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except ImportError:
            return "PyPDF2 package is required to read PDF files."
        except Exception as e:
            return f"Error reading PDF: {str(e)}"