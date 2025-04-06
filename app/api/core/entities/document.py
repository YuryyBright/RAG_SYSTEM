# app/core/entities/document.py
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Document:
    """
    Document entity representing a piece of content to be indexed.

    Attributes:
        id (str): A unique identifier for the document.
        content (str): The main content of the document.
        metadata (Dict[str, Any]): Additional metadata associated with the document, such as tags or categories.
        embedding (Optional[List[float]]): A vector representation of the document content, used for similarity searches.
        created_at (datetime): The timestamp when the document was created. Defaults to the current time.
        updated_at (datetime): The timestamp when the document was last updated. Defaults to the current time.
    """
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()