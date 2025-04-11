# app/core/interfaces/theme_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.core.entities.theme import Theme


class ThemeRepositoryInterface(ABC):
    """
    Interface for theme repository operations.

    This abstract class defines the methods that any theme repository
    implementation must provide to work with the theme system.
    """

    @abstractmethod
    async def create_theme(self, name: str, description: Optional[str],
                           is_public: bool, owner_id: str) -> str:
        """
        Create a new theme.

        Args:
            name: Name of the theme
            description: Optional description of the theme
            is_public: Whether the theme is publicly accessible
            owner_id: ID of the user who owns the theme

        Returns:
            str: ID of the created theme
        """
        pass

    @abstractmethod
    async def get_theme(self, theme_id: str) -> Optional[Theme]:
        """
        Retrieve a theme by its ID.

        Args:
            theme_id: ID of the theme to retrieve

        Returns:
            Optional[Theme]: The theme if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_themes(self, owner_id: Optional[str] = None,
                         include_public: bool = False) -> List[Theme]:
        """
        Get themes filtered by owner and public status.

        Args:
            owner_id: Optional owner ID to filter by
            include_public: Whether to include public themes

        Returns:
            List[Theme]: List of themes matching the criteria
        """
        pass

    @abstractmethod
    async def update_theme(self, theme_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a theme's properties.

        Args:
            theme_id: ID of the theme to update
            updates: Dictionary of properties to update

        Returns:
            bool: True if updated successfully, False otherwise
        """
        pass

    @abstractmethod
    async def delete_theme(self, theme_id: str) -> bool:
        """
        Delete a theme.

        Args:
            theme_id: ID of the theme to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def add_document_to_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Add a document to a theme.

        Args:
            theme_id: ID of the theme
            document_id: ID of the document to add

        Returns:
            bool: True if added successfully, False otherwise
        """
        pass

    @abstractmethod
    async def remove_document_from_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Remove a document from a theme.

        Args:
            theme_id: ID of the theme
            document_id: ID of the document to remove

        Returns:
            bool: True if removed successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_theme_documents(self, theme_id: str) -> List[str]:
        """
        Get the document IDs associated with a theme.

        Args:
            theme_id: ID of the theme

        Returns:
            List[str]: List of document IDs
        """
        pass