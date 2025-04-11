# app/infrastructure/database/repository/file_repository.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.db_models import File
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

    async def create_file(self, **kwargs) -> File:
        """
        Create a new file record in the database.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments corresponding to File model fields.

        Returns
        -------
        File
            The created File object.
        """
        file = File(**kwargs)
        self.db.add(file)
        await self.db.commit()
        await self.db.refresh(file)
        logger.info(f"Created file: {file.filename} (ID: {file.id})")
        return file

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from the database by its ID.

        Parameters
        ----------
        file_id : str
            The unique identifier of the file to delete.

        Returns
        -------
        bool
            True if the file was successfully deleted, False otherwise.
        """
        file = await self.get_by_id(file_id)
        if not file:
            logger.warning(f"Attempted to delete non-existent file: {file_id}")
            return False

        await self.db.delete(file)
        await self.db.commit()
        logger.info(f"Deleted file: {file_id}")
        return True
