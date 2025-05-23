# app/infrastructure/database/repository/file_repository.py
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.db_models import File, ThemeFile, Document
from app.utils.logger_util import get_logger

logger = get_logger(__name__)

class FileRepository:
    """
    Repository class for managing file-related database operations.

    This class provides an abstraction layer over direct database queries
    for file management, including retrieval, creation, and deletion of files.

    Attributes
    ----------
    db : AsyncSession
        The asynchronous database session used for executing queries.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the FileRepository with a database session.

        Parameters
        ----------
        db : AsyncSession
            An active SQLAlchemy async session for database operations.
        """
        self.db = db

    async def get_by_id(self, file_id: str):
        """
        Retrieve a file by its unique ID.

        Parameters
        ----------
        file_id : str
            The unique identifier of the file.

        Returns
        -------
        File or None
            The File object if found, otherwise None.
        """
        result = await self.db.execute(select(File).where(File.id == file_id))
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: str):
        """
        Retrieve all files belonging to a specific user.

        Parameters
        ----------
        owner_id : str
            The ID of the user who owns the files.

        Returns
        -------
        List[File]
            A list of File objects owned by the user.
        """
        result = await self.db.execute(select(File).where(File.owner_id == owner_id))
        return result.scalars().all()

    async def link_file_to_theme(self, file_id: str, theme_id: str) -> None:
        """
        Link a file to a theme by creating an association in the database.

        Parameters
        ----------
        file_id : str
            The unique identifier of the file to link.
        theme_id : str
            The unique identifier of the theme to link the file to.

        Returns
        -------
        None

        Notes
        -----
        This method creates a new record in the `ThemeFile` table to establish
        the relationship between the file and the theme.
        """
        from app.infrastructure.database.db_models import ThemeFile

        link = ThemeFile(file_id=file_id, theme_id=theme_id)
        self.db.add(link)
        await self.db.commit()

    async def create_file(
        self,
        filename: str,
        file_path: str,
        content_type: str,
        owner_id: str,
        size:int,
        theme_id: Optional[str] = None,
        is_public: bool = False
    ) -> File:
        """
        Create and persist a new file record in the database.

        Parameters
        ----------
        filename : str
            Original name of the uploaded file.
        file_path : str
            Path where the file is stored on disk.
        content_type : str
            MIME type of the file (e.g., 'application/pdf').
        owner_id : str
            ID of the user who owns the file.
        size: int
            Size of the file in bytes.
        theme_id : Optional[str], optional
            Associated theme/category ID for organizing files.
        is_public : bool, optional
            Whether the file is publicly accessible (default is False).

        Returns
        -------
        File
            The created File ORM object.
        """
        new_file = File(
            filename=filename,
            file_path=file_path,
            content_type=content_type,
            owner_id=owner_id,
            theme_id=theme_id,
            size=size,
            is_public=is_public
        )
        self.db.add(new_file)
        await self.db.commit()
        await self.db.refresh(new_file)
        logger.info(f"Created file: {filename} (ID: {new_file.id}) for user: {owner_id}")
        return new_file

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file and all related data: documents, theme links, and metadata.

        Args:
            file_id (str): The ID of the file to delete.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """

        try:
            # 1. Delete Theme-File junctions
            await self.db.execute(
                delete(ThemeFile).where(ThemeFile.file_id == file_id)
            )

            # 2. Delete Documents linked to this file (will cascade delete their metadata)
            await self.db.execute(
                delete(Document).where(Document.file_id == file_id)
            )

            # 3. Delete the File itself
            await self.db.execute(
                delete(File).where(File.id == file_id)
            )

            await self.db.commit()
            logger.info(f"[FileRepository] Successfully deleted file and all related data: {file_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"[FileRepository] Error deleting file {file_id}: {e}")
            return False

    async def get_file_by_id(self, file_id: str) -> Optional[File]:
        """
        Retrieve a file record by its unique ID.

        Parameters
        ----------
        file_id : str
            The unique identifier of the file to retrieve.

        Returns
        -------
        Optional[FileModel]
            The `FileModel` object if found, otherwise `None`.

        Notes
        -----
        This method uses the asynchronous session to fetch the file record
        directly by its primary key.
        """
        result = await self.db.get(File, file_id)
        return result

    async def get_file_by_path(self, file_path: str) -> Optional[File]:
        """
        Retrieve a file record by its unique ID.

        Parameters
        ----------
        file_path : str
            The unique path of the file to retrieve.

        Returns
        -------
        Optional[FileModel]
            The `FileModel` object if found, otherwise `None`.

        Notes
        -----
        This method uses the asynchronous session to fetch the file record
        directly by its primary key.
        """
        result = await self.db.execute(select(File).where(File.file_path == file_path))
        return result.scalars().one_or_none()