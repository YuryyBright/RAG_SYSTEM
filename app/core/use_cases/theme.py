# app/core/use_cases/theme.py
from typing import List, Optional, Dict, Any
from datetime import datetime

from infrastructure.repositories.theme_repository import ThemeRepository
from modules.storage.document_store import DocumentStore
from modules.storage.file_manager import FileManager

from domain.entities.document import Document
from infrastructure.database.db_models import File, Theme

from utils.logger_util import get_logger

logger = get_logger(__name__)

class ThemeUseCase:
    """
    Theme use cases implementing business logic for theme management.

    This class handles operations related to themes, including:
    - Creating and updating themes
    - Managing documents within themes
    - Retrieving themes and their documents
    """

    def __init__(
            self,
            theme_repository: ThemeRepository,
            document_store: DocumentStore,
            file_manager: FileManager,
    ):
        """
        Initialize the theme use cases.

        Args:
            theme_repository: Repository for theme operations
            document_store: Store for document operations
        """
        self.theme_repository = theme_repository
        self.document_store = document_store
        self.file_manager = file_manager

    async def create_theme(
            self,
            name: str,
            description: Optional[str],
            is_public: bool,
            owner_id: str
    ) -> Theme:
        """
        Create a new theme.

        Args:
            name: Name of the theme
            description: Optional description of the theme
            is_public: Whether the theme is publicly accessible
            owner_id: ID of the user who owns the theme

        Returns:
            Theme: The created theme entity
        """
        theme_id = await self.theme_repository.create_theme(
            name=name,
            description=description,
            is_public=is_public,
            owner_id=owner_id
        )

        return Theme(
            id=theme_id,
            name=name,
            description=description,
            is_public=is_public,
            owner_id=owner_id,
            created_at=datetime.utcnow(),
            document_ids=[]
        )

    async def get_theme(self, theme_id: str) -> Optional[Theme]:
        """
        Get a theme by its ID.

        Args:
            theme_id: ID of the theme

        Returns:
            Optional[Theme]: The theme if found, None otherwise
        """
        return await self.theme_repository.get_theme(theme_id)

    async def get_themes(
            self,
            owner_id: Optional[str] = None,
            include_public: bool = False
    ) -> List[Theme]:
        """
        Get themes filtered by owner and public status.

        Args:
            owner_id: Optional owner ID to filter by
            include_public: Whether to include public themes

        Returns:
            List[Theme]: List of themes matching the criteria
        """
        return await self.theme_repository.get_themes(
            owner_id=owner_id,
            include_public=include_public
        )

    async def update_theme(
            self,
            theme_id: str,
            updates: Dict[str, Any]
    ) -> bool:
        """
        Update a theme's properties.

        Args:
            theme_id: ID of the theme to update
            updates: Dictionary of properties to update

        Returns:
            bool: True if updated successfully, False otherwise
        """
        # Filter out None values
        filtered_updates = {k: v for k, v in updates.items() if v is not None}

        if not filtered_updates:
            return True  # Nothing to update

        return await self.theme_repository.update_theme(theme_id, filtered_updates)

    async def delete_theme(self, theme_id: str) -> bool:
        """
        Delete a theme along with its files and documents from disk and database.

        Args:
            theme_id (str): ID of the theme to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            # 1. Delete files from disk
            files = await self.theme_repository.get_files_by_theme(theme_id)
            for file in files:
                await self.file_manager.delete_file(file.file_path)

            # 2. Delete documents from disk
            documents = await self.theme_repository.get_direct_documents_by_theme(theme_id)
            for doc in documents:
                self.document_store._delete_document_from_disk(
                    document_id=doc.id,
                    owner_id=doc.owner_id,
                    theme_id=doc.theme_id
                )

            # 3. Finally delete everything in DB
            return await self.theme_repository.delete_theme(theme_id)

        except Exception as e:
            logger.exception(f"Failed to delete theme {theme_id}: {e}")
            return False

    async def add_document_to_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Add a document to a theme.

        Args:
            theme_id: ID of the theme
            document_id: ID of the document to add

        Returns:
            bool: True if added successfully, False otherwise
        """
        # Verify document exists
        document = await self.document_store.get_document(document_id)
        if not document:
            return False

        return await self.theme_repository.add_document_to_theme(theme_id, document_id)

    async def remove_document_from_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Remove a document from a theme.

        Args:
            theme_id: ID of the theme
            document_id: ID of the document to remove

        Returns:
            bool: True if removed successfully, False otherwise
        """
        return await self.theme_repository.remove_document_from_theme(theme_id, document_id)

    async def get_theme_documents(self, theme_id: str) -> List[Document]:
        """
        Get the documents associated with a theme.

        Args:
            theme_id: ID of the theme

        Returns:
            List[Document]: List of document entities
        """
        document_ids = await self.theme_repository.get_theme_documents(theme_id)

        documents = []
        for doc_id in document_ids:
            document = await self.document_store.get_document(doc_id)
            if document:
                documents.append(document)

        return documents

    async def get_theme_files(self, theme_id: str) -> List[File]:
        """
        Get the files associated with a theme.

        Args:
            theme_id: ID of the theme

        Returns:
            List[Files]: List of files entities
        """
        return await self.theme_repository.get_theme_files(theme_id)

