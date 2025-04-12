from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.infrastructure.database.db_models import Theme, ThemeDocument, Document
from app.utils.logger_util import get_logger
from core.interfaces.theme_repository import ThemeRepositoryInterface

logger = get_logger(__name__)

class ThemeRepository(ThemeRepositoryInterface):
    """
    Repository for managing theme-related database operations.

    This class handles CRUD operations for themes, manages document associations
    with themes, and encapsulates SQLAlchemy database session logic.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the ThemeRepository.

        Args:
            db (AsyncSession): The async SQLAlchemy database session.
        """
        self.db = db

    async def create_theme(self, name: str, description: Optional[str],
                         is_public: bool, owner_id: str) -> str:
        """
        Create and persist a new theme in the database.

        Args:
            name (str): Name of the theme.
            description (Optional[str]): Optional description of the theme.
            is_public (bool): Flag to indicate if the theme is publicly accessible.
            owner_id (str): ID of the user who owns this theme.

        Returns:
            str: The ID of the newly created theme.

        Raises:
            SQLAlchemyError: If a database error occurs.
        """
        try:
            theme = Theme(
                name=name,
                description=description,
                is_public=is_public,
                owner_id=owner_id,
                created_at=datetime.utcnow()
            )
            self.db.add(theme)
            await self.db.commit()
            return theme.id
        except SQLAlchemyError as e:
            logger.error(f"Error creating theme: {e}")
            await self.db.rollback()
            raise

    async def get_theme(self, theme_id: str) -> Optional[Theme]:
        """
        Retrieve a single theme by its ID.

        Args:
            theme_id (str): ID of the theme to retrieve.

        Returns:
            Optional[Theme]: The theme object if found, else None.
        """
        try:
            result = await self.db.execute(
                select(Theme).where(Theme.id == theme_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching theme {theme_id}: {e}")
            return None

    async def get_themes(self, owner_id: Optional[str] = None,
                         include_public: bool = False) -> List[Theme]:
        """
        Retrieve a list of themes filtered by owner and/or public visibility.

        Args:
            owner_id (Optional[str]): User ID to filter by ownership.
            include_public (bool): If True, also include publicly visible themes.

        Returns:
            List[Theme]: List of matching Theme objects.
        """
        try:
            query = select(Theme).options(selectinload(Theme.documents))  # ✅ this line preloads documents

            if owner_id:
                if include_public:
                    query = query.where((Theme.owner_id == owner_id) | (Theme.is_public == True))
                else:
                    query = query.where(Theme.owner_id == owner_id)
            elif include_public:
                query = query.where(Theme.is_public == True)

            result = await self.db.execute(query)
            return list(result.scalars())
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving themes: {e}")
            return []

    async def update_theme(self, theme_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a theme's attributes.

        Args:
            theme_id (str): ID of the theme to update.
            updates (Dict[str, Any]): Dictionary of fields to update.

        Returns:
            bool: True if update succeeded, False otherwise.
        """
        try:
            stmt = (
                update(Theme)
                .where(Theme.id == theme_id)
                .values(**updates)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"Error updating theme {theme_id}: {e}")
            await self.db.rollback()
            return False

    async def delete_theme(self, theme_id: str) -> bool:
        """
        Delete a theme and all of its document associations.

        Args:
            theme_id (str): ID of the theme to delete.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        try:
            await self.db.execute(
                delete(ThemeDocument).where(ThemeDocument.theme_id == theme_id)
            )
            result = await self.db.execute(
                delete(Theme).where(Theme.id == theme_id)
            )
            await self.db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"Error deleting theme {theme_id}: {e}")
            await self.db.rollback()
            return False

    async def add_document_to_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Associate a document with a theme.

        Args:
            theme_id (str): ID of the theme.
            document_id (str): ID of the document to associate.

        Returns:
            bool: True if successfully associated, False otherwise.
        """
        try:
            # Verify document exists
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            if not result.scalar_one_or_none():
                return False

            # Check if already associated
            existing = await self.db.execute(
                select(ThemeDocument).where(
                    and_(
                        ThemeDocument.theme_id == theme_id,
                        ThemeDocument.document_id == document_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                return True

            # Add new association
            link = ThemeDocument(
                theme_id=theme_id,
                document_id=document_id
            )
            self.db.add(link)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error linking document {document_id} to theme {theme_id}: {e}")
            await self.db.rollback()
            return False

    async def remove_document_from_theme(self, theme_id: str, document_id: str) -> bool:
        """
        Remove the association between a document and a theme.

        Args:
            theme_id (str): ID of the theme.
            document_id (str): ID of the document to disassociate.

        Returns:
            bool: True if disassociation succeeded, False otherwise.
        """
        try:
            stmt = delete(ThemeDocument).where(
                and_(
                    ThemeDocument.theme_id == theme_id,
                    ThemeDocument.document_id == document_id
                )
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"Error unlinking document {document_id} from theme {theme_id}: {e}")
            await self.db.rollback()
            return False

    async def get_theme_documents(self, theme_id: str) -> List[str]:
        """
        Retrieve document IDs associated with a theme.

        Args:
            theme_id (str): ID of the theme.

        Returns:
            List[str]: List of associated document IDs.
        """
        try:
            result = await self.db.execute(
                select(ThemeDocument.document_id).where(
                    ThemeDocument.theme_id == theme_id
                )
            )
            return list(result.scalars())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching documents for theme {theme_id}: {e}")
            return []
