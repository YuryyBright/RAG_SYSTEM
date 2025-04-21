from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select, update, delete, and_, func  # ADDED func for counting
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.infrastructure.database.db_models import Theme, ThemeDocument, Document, ProcessingTask, ThemeShare
from app.utils.logger_util import get_logger
from core.interfaces.theme_repository import ThemeRepositoryInterface
from app.infrastructure.database.db_models import File, ThemeFile
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
            query = select(Theme).options(selectinload(Theme.documents))

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
        Delete a theme and all of its related data: documents, files, tasks, etc.

        Args:
            theme_id (str): ID of the theme to delete.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        try:
            # 1. Delete ThemeDocument links (many-to-many table)
            await self.db.execute(
                delete(ThemeDocument).where(ThemeDocument.theme_id == theme_id)
            )

            # 2. Delete Documents (because they depend on Files and Theme)
            await self.db.execute(
                delete(Document).where(Document.theme_id == theme_id)
            )

            # 3. Delete ThemeFile links (many-to-many table)
            await self.db.execute(
                delete(ThemeFile).where(ThemeFile.theme_id == theme_id)
            )

            # 4. Delete Files (now it's safe because no Documents depend on them)
            await self.db.execute(
                delete(File).where(File.theme_id == theme_id)
            )

            # 5. Delete Tasks (optional, not blocked but good cleanup)
            await self.db.execute(
                delete(ProcessingTask).where(ProcessingTask.theme_id == theme_id)
            )

            # 6. Delete Shares (optional, not blocked but good cleanup)
            await self.db.execute(
                delete(ThemeShare).where(ThemeShare.theme_id == theme_id)
            )

            # 7. Finally delete the Theme
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

    async def get_files_by_theme(self, theme_id: str) -> List[File]:
        """
        Retrieve all files directly associated with a theme.

        Args:
            theme_id (str): ID of the theme.

        Returns:
            List[File]: List of files.
        """
        try:
            result = await self.db.execute(
                select(File).where(File.theme_id == theme_id)
            )
            return list(result.scalars())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching files for theme {theme_id}: {e}")
            return []

    async def get_direct_documents_by_theme(self, theme_id: str) -> List[Document]:
        """
        Retrieve all documents directly attached to a theme (by theme_id field).

        Args:
            theme_id (str): ID of the theme.

        Returns:
            List[Document]: List of documents.
        """
        try:
            result = await self.db.execute(
                select(Document).where(Document.theme_id == theme_id)
            )
            return list(result.scalars())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching documents for theme {theme_id}: {e}")
            return []
    async def count_documents(self, theme_id: str) -> int:
        """
        Count the number of documents associated with a theme.

        Args:
            theme_id (str): ID of the theme.

        Returns:
            int: The count of associated documents.
        """
        try:
            result = await self.db.execute(
                select(func.count(ThemeDocument.document_id)).where(
                    ThemeDocument.theme_id == theme_id
                )
            )
            return result.scalar_one_or_none() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting documents for theme {theme_id}: {e}")
            return 0

    async def add_file_to_theme(self, theme_id: str, file_id: str) -> bool:
        """
        Associate a file with a theme.

        Args:
            theme_id (str): ID of the theme.
            file_id (str): ID of the file to associate.

        Returns:
            bool: True if successfully associated, False otherwise.
        """

        try:
            # Verify file exists
            result = await self.db.execute(
                select(File).where(File.id == file_id)
            )
            if not result.scalar_one_or_none():
                return False

            # Check if already associated
            existing = await self.db.execute(
                select(ThemeFile).where(
                    and_(
                        ThemeFile.theme_id == theme_id,
                        ThemeFile.file_id == file_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                return True

            # Add new association
            link = ThemeFile(
                theme_id=theme_id,
                file_id=file_id
            )
            self.db.add(link)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error linking file {file_id} to theme {theme_id}: {e}")
            await self.db.rollback()
            return False

    async def remove_file_from_theme(self, theme_id: str, file_id: str) -> bool:
        """
        Remove the association between a file and a theme.

        Args:
            theme_id (str): ID of the theme.
            file_id (str): ID of the file to disassociate.

        Returns:
            bool: True if disassociation succeeded, False otherwise.
        """

        try:
            stmt = delete(ThemeFile).where(
                and_(
                    ThemeFile.theme_id == theme_id,
                    ThemeFile.file_id == file_id
                )
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            logger.error(f"Error unlinking file {file_id} from theme {theme_id}: {e}")
            await self.db.rollback()
            return False

    async def get_theme_files(self, theme_id: str) -> List[Any]:
        """
        Retrieve File objects associated with a theme.

        Args:
            theme_id (str): ID of the theme.

        Returns:
            List[File]: List of associated File objects.
        """

        try:
            result = await self.db.execute(
                select(File)
                .join(ThemeFile, ThemeFile.file_id == File.id)
                .where(ThemeFile.theme_id == theme_id)
            )
            return list(result.scalars())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching files for theme {theme_id}: {e}")
            return []
