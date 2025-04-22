# app/core/entities/theme.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Theme:
    """
    Represents a theme entity for grouping documents.

    Attributes
    ----------
    id : str
        Unique identifier for the theme.
    name : str
        Name of the theme.
    description : Optional[str]
        Description of the theme (optional).
    is_public : bool
        Indicates if the theme is publicly accessible.
    owner_id : str
        ID of the user who owns the theme.
    created_at : datetime
        Timestamp when the theme was created.
    updated_at : Optional[datetime]
        Timestamp when the theme was last updated (optional).
    document_ids : List[str]
        List of document IDs associated with the theme.
    """
    id: str
    name: str
    description: Optional[str]
    is_public: bool
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_ids: List[str] = None
