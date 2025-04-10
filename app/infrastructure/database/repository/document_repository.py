# app/infrastructure/database/repository/document_repository.py
from typing import Optional, List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.db_models import Document, DocumentMetadata
from app.utils.logger_util import get_logger

logger = get_logger(__name__)

class DocumentRepository:
    """
    Repository class for managing document-related database operations.

    Provides high-level methods for retrieving, storing, and managing documents
    and their associated metadata in a structured and reusable way.

    Attributes
    ----------
    db : AsyncSession
        The asynchronous SQLAlchemy session used for DB communication.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the DocumentRepository with a database session.

        Parameters
        ----------
        db : AsyncSession
            The asynchronous SQLAlchemy session for executing queries.
        """
        self.db = db

    async def get_by_id(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by its unique ID.

        Parameters
        ----------
        document_id : str
            The unique identifier of the document.

        Returns
        -------
        Document or None
            The Document object if found, otherwise None.
        """
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: str) -> List[Document]:
        """
        Retrieve all documents associated with a specific user.

        Parameters
        ----------
        owner_id : str
            The ID of the user who owns the documents.

        Returns
        -------
        List[Document]
            A list of Document objects owned by the user.
        """
        result = await self.db.execute(select(Document).where(Document.owner_id == owner_id))
        return result.scalars().all()

    async def create_document(self, **kwargs) -> Document:
        """
        Create a new document record in the database.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments matching the Document model fields.

        Returns
        -------
        Document
            The created Document object.
        """
        doc = Document(**kwargs)
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        logger.info(f"Created document (ID: {doc.id}) for user: {doc.owner_id}")
        return doc

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and its metadata by ID.

        Parameters
        ----------
        document_id : str
            The unique identifier of the document to delete.

        Returns
        -------
        bool
            True if the document was deleted, False otherwise.
        """
        doc = await self.get_by_id(document_id)
        if not doc:
            logger.warning(f"Document not found: {document_id}")
            return False

        await self.db.delete(doc)
        await self.db.commit()
        logger.info(f"Deleted document: {document_id}")
        return True

    async def get_all(self) -> List[Document]:
        """
        Retrieve all documents from the database.

        Returns
        -------
        List[Document]
            A list of all document entities.
        """
        result = await self.db.execute(select(Document))
        return result.scalars().all()