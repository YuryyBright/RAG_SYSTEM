from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentBase(BaseModel):
    """
    Base schema for document data.

    Attributes
    ----------
    content : str
        The main content of the document.
    metadata : Dict[str, Any]
        Additional metadata associated with the document, such as tags or categories.
    """
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")

class DocumentCreate(DocumentBase):
    """
    Schema for creating a new document.

    Inherits from DocumentBase and does not add any additional fields.
    """
    pass

class DocumentResponse(DocumentBase):
    """
    Schema for document response.

    Attributes
    ----------
    id : str
        A unique identifier for the document.
    created_at : datetime
        The timestamp when the document was created.
    updated_at : datetime
        The timestamp when the document was last updated.
    """
    id: str = Field(..., description="Document ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True