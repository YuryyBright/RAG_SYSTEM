from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.db_models import Document
from app.utils.logger_util import get_logger

logger = get_logger(__name__)

class DocumentRepository:
    """
    Repository class for managing document-related database operations.

    Provides high-level methods for retrieving, storing, and managing documents
    and their associated metadata in a structured and reusable way.
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
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
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
        result = await self.db.execute(
            select(Document).where(Document.owner_id == owner_id)
        )
        return result.scalars().all()

    async def create_document(self, **kwargs) -> str:
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

        if "content" not in kwargs:
            raise ValueError("'content' are required.")
        doc = Document(**kwargs)
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        logger.info(f"Created document (ID: {doc.id}) for user: {doc.owner_id}")
        return doc.id

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

    async def get_by_file_id(self, file_id: str) -> List[Document]:
        """
        Retrieve all documents that originated from a specific file.

        Parameters
        ----------
        file_id : str
            The ID of the source file.

        Returns
        -------
        List[Document]
            Documents linked to the specified file.
        """
        result = await self.db.execute(
            select(Document).where(Document.file_id == file_id)
        )
        return result.scalars().all()

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

    async def delete_by_file_id(self, file_id: str) -> int:
        """
        Delete all documents linked to a file.

        Returns
        -------
        int: Number of documents deleted.
        """
        documents = await self.get_by_file_id(file_id)
        count = len(documents)
        for doc in documents:
            await self.db.delete(doc)
        await self.db.commit()
        logger.info(f"Deleted {count} document(s) for file: {file_id}")
        return count

    async def get_documents(self, ids: List[str]) -> List[Document]:
        """
        Retrieve documents by a list of IDs.
        """
        result = await self.db.execute(
            select(Document).where(Document.id.in_(ids))
        )
        return result.scalars().all()

    async def get_all_documents(self, owner_id: Optional[str] = None) -> List[Document]:
        """
        Retrieve all documents, optionally filtered by owner.
        """
        stmt = select(Document)
        if owner_id:
            stmt = stmt.where(Document.owner_id == owner_id)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_document(
            self, document_id: str, content: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> bool:
        """
        Update document fields.
        """
        doc = await self.get_by_id(document_id)
        if not doc:
            return False

        doc.content = content
        doc.embedding = embedding
        doc.metadata = metadata

        await self.db.commit()
        return True

    async def count_documents(self, filter_criteria: Dict[str, Any] = None) -> int:
        """
        Count documents based on filter criteria.
        """
        stmt = select(func.count()).select_from(Document)

        if filter_criteria:
            conditions = []
            for key, value in filter_criteria.items():
                if hasattr(Document, key):
                    conditions.append(getattr(Document, key) == value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.db.execute(stmt)
        return result.scalar()

    async def search_similar(
            self, embedding: Optional[List[float]], limit: int = 10, owner_id: Optional[str] = None
    ) -> List[Document]:
        """
        Search for similar documents using a vector embedding. This assumes
        a method is in place (e.g., FAISS or Postgres pgvector) that supports vector similarity.
        """
        # Placeholder stub — to be implemented based on your similarity method (e.g., cosine similarity).
        raise NotImplementedError("Vector similarity search not yet implemented.")