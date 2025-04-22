# app/infrastructure/loaders/readers/reader_factory.py
from pathlib import Path
from typing import Dict, Type

from .base_reader import BaseReader
from .txt_reader import TxtReader
from .json_reader import JsonReader
from .html_reader import HtmlReader
from .pdf_reader import PdfReader
from .docx_reader import DocxReader
from .csv_reader import CsvReader
from .xlsx_reader import XlsxReader
from .xml_reader import XmlReader
from .pptx_reader import PptxReader
from .rtf_reader import RtfReader
from .yaml_reader import YamlReader

# Import other readers here


class ReaderFactory:
    """
    Factory for creating file readers based on file extension.
    """

    # Map extensions to reader classes
    _readers: Dict[str, Type[BaseReader]] = {
        ".txt": TxtReader,
        ".md": TxtReader,
        ".markdown": TxtReader,
        ".json": JsonReader,
        ".html": HtmlReader,
        ".htm": HtmlReader,
        ".pdf": PdfReader,
        ".docx": DocxReader,
        ".csv": CsvReader,
        ".xlsx": XlsxReader,
        ".xml": XmlReader,
        ".pptx": PptxReader,
        ".rtf": RtfReader,
        ".yaml": YamlReader,
        ".yml": YamlReader,
        # Add more mappings as readers are implemented
    }

    @classmethod
    def get_reader(cls, file_path: Path) -> BaseReader:
        """
        Get the appropriate reader for a file.

        Parameters
        ----------
        file_path : Path
            Path of the file.

        Returns
        -------
        BaseReader
            Reader instance appropriate for the file.

        Raises
        ------
        ValueError
            If no reader is available for the file extension.
        """
        extension = file_path.suffix.lower()

        reader_class = cls._readers.get(extension)
        if reader_class:
            return reader_class()
        else:
            raise ValueError(f"No reader available for extension: {extension}")

    @classmethod
    def register_reader(cls, extension: str, reader_class: Type[BaseReader]) -> None:
        """
        Register a new reader for a file extension.

        Parameters
        ----------
        extension : str
            File extension (including dot, e.g., ".docx").
        reader_class : Type[BaseReader]
            Reader class to use for this extension.
        """
        cls._readers[extension.lower()] = reader_class