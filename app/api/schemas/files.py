# app/api/schemas/files.py
from datetime import datetime
from pydantic import BaseModel, Field


class FileResponse(BaseModel):
    """
    Schema for file response.

    Attributes
    ----------
    id : str
        The unique identifier of the file.
    filename : str
        The name of the file.
    content_type : str
        The MIME type of the file.
    size : int
        The size of the file in bytes.
    is_public : bool
        Whether the file is publicly accessible.
    created_at : datetime
        The timestamp when the file was uploaded.
    """
    id: str = Field(..., description="File ID")
    filename: str = Field(..., description="File name")
    content_type: str = Field(..., description="File MIME type")
    size: int = Field(..., description="File size in bytes")
    is_public: bool = Field(..., description="Whether the file is public")
    created_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        orm_mode = True