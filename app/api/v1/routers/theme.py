# app/api/v1/routes/themes.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.files import FileResponse
from app.api.dependencies.dependencies import get_theme_use_case
from app.api.schemas.theme import (
    ThemeCreate,
    ThemeUpdate,
    ThemeResponse,
    ThemeDetailResponse,
    DocumentToTheme
)

from app.api.middleware_auth import get_current_active_user
from app.core.use_cases.theme import ThemeUseCase
from app.core.interfaces.document_store import DocumentStoreInterface
from app.api.dependencies.dependencies import get_document_store
from core.entities.user import User

router = APIRouter()

@router.post("/", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
        theme_data: ThemeCreate,
        user: dict = Depends(get_current_active_user),
        theme_use_case: ThemeUseCase = Depends(get_theme_use_case)
):
    """
    Create a new theme.
    """
    try:
        created_theme = await theme_use_case.create_theme(
            name=theme_data.name,
            description=theme_data.description,
            is_public=theme_data.is_public,
            owner_id=user.id
        )

        return ThemeResponse(
            id=created_theme.id,
            name=created_theme.name,
            description=created_theme.description,
            is_public=created_theme.is_public,
            owner_id=created_theme.owner_id,
            document_count=await theme_use_case.theme_repository.count_documents(created_theme.id),
            created_at=created_theme.created_at.isoformat(),
            updated_at=created_theme.updated_at.isoformat() if created_theme.updated_at else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create theme: {str(e)}"
        )


@router.get("/", response_model=List[ThemeResponse])
async def get_themes(
        include_public: bool = False,
        user: dict = Depends(get_current_active_user),
        theme_use_case: ThemeUseCase = Depends(get_theme_use_case)
):
    """
    Get themes owned by the current user, optionally including public themes.
    """
    try:
        themes = await theme_use_case.get_themes(
            owner_id=user.id,  # ✅ FIXED HERE
            include_public=include_public
        )

        # Add document count to each theme
        result = []
        for theme in themes:
            document_ids = [doc.document_id for doc in theme.documents] if theme.documents else []
            result.append({
                "id": theme.id,
                "name": theme.name,
                "description": theme.description,
                "is_public": theme.is_public,
                "owner_id": theme.owner_id,
                "created_at": theme.created_at.isoformat() if theme.created_at else None,
                "updated_at": theme.updated_at.isoformat() if theme.updated_at else None,
                "document_count": len(document_ids)
            })

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve themes: {str(e)}"
        )


@router.get("/{theme_id}", response_model=ThemeDetailResponse)
async def get_theme(
        theme_id: str,
        user: dict = Depends(get_current_active_user),
        theme_use_case: ThemeUseCase = Depends(get_theme_use_case)
):
    """
    Get a specific theme by ID.
    """
    try:
        theme = await theme_use_case.get_theme(theme_id)

        if not theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )

        # Check if user has access to the theme
        if theme.owner_id != user.id and not theme.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this theme"
            )

        return {
            "id": theme.id,
            "name": theme.name,
            "description": theme.description,
            "is_public": theme.is_public,
            "owner_id": theme.owner_id,
            "created_at": theme.created_at,
            "updated_at": theme.updated_at,
            "document_count": len(theme.document_ids or []),
            "document_ids": theme.document_ids or []
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve theme: {str(e)}"
        )


@router.put("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    theme_id: str,
    theme_data: ThemeUpdate,
    user: dict = Depends(get_current_active_user),
    theme_use_case: ThemeUseCase = Depends(get_theme_use_case)
):
    """
    Update a theme.
    """
    try:
        # Check if theme exists and user owns it
        existing_theme = await theme_use_case.get_theme(theme_id)
        if not existing_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )

        if existing_theme.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this theme"
            )

        # Update theme
        updates = theme_data.dict(exclude_unset=True, exclude_none=True)
        if not updates:
            # Nothing to update
            return {
                "id": existing_theme.id,
                "name": existing_theme.name,
                "description": existing_theme.description,
                "is_public": existing_theme.is_public,
                "owner_id": existing_theme.owner_id,
                "created_at": existing_theme.created_at,
                "updated_at": existing_theme.updated_at,
                "document_count": len(existing_theme.document_ids or [])
            }

        success = await theme_use_case.update_theme(theme_id, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update theme"
            )

        # Get updated theme
        updated_theme = await theme_use_case.get_theme(theme_id)

        return {
            "id": updated_theme.id,
            "name": updated_theme.name,
            "description": updated_theme.description,
            "is_public": updated_theme.is_public,
            "owner_id": updated_theme.owner_id,
            "created_at": updated_theme.created_at,
            "updated_at": updated_theme.updated_at,
            "document_count": len(updated_theme.document_ids or [])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update theme: {str(e)}"
        )


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(
    theme_id: str,
    user: User = Depends(get_current_active_user),
    theme_use_case: ThemeUseCase = Depends(get_theme_use_case)
):
    """
    Delete a theme.
    """
    try:
        # Check if theme exists and user owns it
        existing_theme = await theme_use_case.get_theme(theme_id)
        if not existing_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )

        if existing_theme.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this theme"
            )

        # Delete theme
        success = await theme_use_case.delete_theme(theme_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete theme"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete theme: {str(e)}"
        )


@router.post("/{theme_id}/documents", status_code=status.HTTP_200_OK)
async def add_document_to_theme(
    theme_id: str,
    document_data: DocumentToTheme,
    user: dict = Depends(get_current_active_user),
    theme_use_case: ThemeUseCase = Depends(get_theme_use_case),
    document_store: DocumentStoreInterface = Depends(get_document_store)
):
    """
    Add a document to a theme.
    """
    try:
        # Check if theme exists and user owns it
        existing_theme = await theme_use_case.get_theme(theme_id)
        if not existing_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )

        if existing_theme.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this theme"
            )

        # Check if document exists and user has access to it
        document = await document_store.get_document(document_data.document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        if document.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to use this document"
            )

        # Add document to theme
        success = await theme_use_case.add_document_to_theme(
            theme_id,
            document_data.document_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add document to theme"
            )

        return {"message": "Document added to theme successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add document to theme: {str(e)}"
        )


@router.delete("/{theme_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document_from_theme(
    theme_id: str,
    document_id: str,
    user: dict = Depends(get_current_active_user),
    theme_use_case: ThemeUseCase = Depends(get_theme_use_case)
):
    """
    Remove a document from a theme.
    """
    try:
        # Check if theme exists and user owns it
        existing_theme = await theme_use_case.get_theme(theme_id)
        if not existing_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )

        if existing_theme.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this theme"
            )

        # Remove document from theme
        success = await theme_use_case.remove_document_from_theme(theme_id, document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found in theme"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove document from theme: {str(e)}"
        )


@router.get("/{theme_id}/documents", response_model=List[dict])
async def get_theme_documents(
    theme_id: str,
    user: dict = Depends(get_current_active_user),
    theme_use_case: ThemeUseCase = Depends(get_theme_use_case)
):
    """
    Get all documents in a theme.
    """
    try:
        # Check if theme exists and user has access to it
        existing_theme = await theme_use_case.get_theme(theme_id)
        if not existing_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )

        if existing_theme.owner_id != user.id and not existing_theme.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this theme"
            )

        # Get documents
        documents = await theme_use_case.get_theme_documents(theme_id)

        # Convert to response format
        result = []
        for doc in documents:
            result.append({
                "id": doc.id,
                "title": doc.metadata.get("title", "Untitled"),
                "source": doc.metadata.get("source", "Unknown"),
                "created_at": doc.created_at,
                "updated_at": doc.updated_at
            })

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve theme documents: {str(e)}"
        )


@router.get("/{theme_id}/files", response_model=List[FileResponse])
async def get_theme_files(
        theme_id: str,
        user: dict = Depends(get_current_active_user),
        theme_use_case: ThemeUseCase = Depends(get_theme_use_case),
):
    """
    Get all files associated with a theme.
    """
    try:
        # Check if theme exists and user has access to it
        existing_theme = await theme_use_case.get_theme(theme_id)
        if not existing_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )

        if existing_theme.owner_id != user.id and not existing_theme.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this theme"
            )

        # Get documents first to get their IDs
        files_theme = await theme_use_case.get_theme_files(theme_id)

        # Create a list to hold file data
        files = []

        # Process each document to extract file info
        for file in files_theme:
            # Extract relevant file information
            file_info = {
                "id": file.id,
                "filename": file.filename,
                "title": file.filename,  # or extract from a title metadata field if you store it
                "source": "Unknown",  # update if you store this in the File model or metadata
                "size": file.size,
                'content_type':file.content_type,
                'is_public': file.is_public,
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "updated_at": file.updated_at.isoformat() if file.updated_at else None,
            }

            files.append(file_info)

        return files
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve theme files: {str(e)}"
        )