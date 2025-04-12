# app/core/interfaces/theme_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class ThemeRepositoryInterface(ABC):
    """
    Interface for theme repository operations.

    Defines the required methods for interacting with the theme persistence layer.
    """

    @abstractmethod
    async def create_theme(self, name: str, description: Optional[str],
                           is_public: bool, owner_id: str) -> str:
        """
        Create a new theme.

        Args:
            name: Name of the theme.
            description: Optional description of the theme.
            is_public: Whether the theme is public.
            owner_id: ID of the user creating the theme.

        Returns:
            str: The ID of the created theme.
        """
        pass

    @abstractmethod
    async def get_theme(self, theme_id: str) -> Optional[Any]:
        """
        Retrieve a theme by ID.

        Args:
            theme_id: The ID of the theme.

        Returns:
            Optional[Any]: The theme object if found, else None.
        """
        pass

    @abstractmethod
    async def get_themes(self, owner_id: Optional[str] = None,
                         include_public: bool = False) -> List[Any]:
        """
        Get themes filtered by ownership and public visibility.

        Args:
            owner_id: Optional user ID to filter owned themes.
            include_public: Whether to include public themes.

        Returns:
            List[Any]: List of themes.
        """
        pass

    @abstractmethod
    async def update_theme(self, theme_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update fields in a theme.

        Args:
            theme_id: ID of the theme to update.
            updates: Dict of fields and values to update.

        Returns:
            bool: True if update was successful, else False.
        """
        pass

    @abstractmethod
    async def delete_theme(self, theme_id: str) -> bool:
        """
        Delete a theme and its document links.

        Args:
            theme_id: ID of the theme to delete.

        Returns:
            bool: True if deletion was successful, else False.
        """
        pass

    @abstractmethod
    async def add_document_to_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Link a document to a theme.

        Args:
            theme_id: ID of the theme.
            document_id: ID of the document to link.

        Returns:
            bool: True if added successfully, else False.
        """
        pass

    @abstractmethod
    async def remove_document_from_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Remove a document from a theme.

        Args:
            theme_id: ID of the theme.
            document_id: ID of the document to remove.

        Returns:
            bool: True if removal was successful, else False.
        """
        pass

    @abstractmethod
    async def get_theme_documents(self, theme_id: str) -> List[str]:
        """
        Get all document IDs associated with a theme.

        Args:
            theme_id: ID of the theme.

        Returns:
            List[str]: List of document IDs.
        """
        pass
