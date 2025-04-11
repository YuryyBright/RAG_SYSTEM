"""
This module defines Pydantic schemas for themes and related operations.

Schemas:
- ThemeBase: Base schema with common attributes for themes.
- ThemeCreate: Schema for creating a new theme.
- ThemeUpdate: Schema for updating an existing theme.
- ThemeResponse: Schema for theme responses.
- ThemeDetailResponse: Schema for detailed theme responses, including document IDs.
- DocumentToTheme: Schema for adding or removing a document from a theme.
- ThemeExport: Schema for exporting a theme with its documents.
- ThemeImport: Schema for importing a theme with its documents.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ThemeBase(BaseModel):
    """Base theme schema with common attributes."""
    name: str = Field(..., description="Name of the theme")
    description: Optional[str] = Field(None, description="Description of the theme")
    is_public: bool = Field(False, description="Whether the theme is publicly accessible")


class ThemeCreate(ThemeBase):
    """Schema for creating a new theme."""
    pass


class ThemeUpdate(BaseModel):
    """Schema for updating an existing theme."""
    name: Optional[str] = Field(None, description="Name of the theme")
    description: Optional[str] = Field(None, description="Description of the theme")
    is_public: Optional[bool] = Field(None, description="Whether the theme is publicly accessible")


class ThemeResponse(ThemeBase):
    """Schema for theme responses."""
    id: str = Field(..., description="Unique identifier for the theme")
    owner_id: str = Field(..., description="ID of the user who owns the theme")
    created_at: datetime = Field(..., description="Timestamp when the theme was created")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the theme was last updated")
    document_count: int = Field(0, description="Number of documents in the theme")

    class Config:
        orm_mode = True


class ThemeDetailResponse(ThemeResponse):
    """Schema for detailed theme responses including document IDs."""
    document_ids: List[str] = Field([], description="List of document IDs in the theme")


class DocumentToTheme(BaseModel):
    """Schema for adding or removing a document from a theme."""
    document_id: str = Field(..., description="ID of the document")


class ThemeExport(BaseModel):
    """Schema for exporting a theme."""
    theme: ThemeDetailResponse = Field(..., description="Theme details")
    documents: List[dict] = Field([], description="List of documents in the theme")


class ThemeImport(BaseModel):
    """Schema for importing a theme."""
    name: str = Field(..., description="Name of the theme")
    description: Optional[str] = Field(None, description="Description of the theme")
    is_public: bool = Field(False, description="Whether the theme is publicly accessible")
    documents: List[dict] = Field([], description="List of documents to import")