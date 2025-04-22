from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ProcessedFile:
    """
    Entity representing a processed file for the RAG (Retrieval-Augmented Generation) system.

    Attributes
    ----------
    id : str
        Unique identifier for the processed file.
    filename : str
        Name of the file.
    content : str
        Content of the file.
    language : Optional[str], optional
        Detected language of the file content (default is None).
    is_readable : bool, optional
        Indicates whether the file is readable (default is True).
    is_language_detected : bool, optional
        Indicates whether the language of the file content was successfully detected (default is True).
    metadata : Dict[str, Any], optional
        Additional metadata associated with the file (default is None).
    """
    id: str
    filename: str
    content: str
    language: Optional[str] = None
    is_readable: bool = True
    is_language_detected: bool = True
    metadata: Dict[str, Any] = None