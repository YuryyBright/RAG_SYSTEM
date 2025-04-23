from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.db_models import Document, ThemeDocument
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

    async def create_theme_document_link(self, theme_id: str, document_id: str) -> None:
        """
        Create a link between a Theme and a Document in the ThemeDocument table.

        Args:
            theme_id: ID of the theme
            document_id: ID of the document
        """

        theme_document = ThemeDocument(
            theme_id=theme_id,
            document_id=document_id
        )
        self.db.add(theme_document)
        await  self.db.commit()
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
            self,
            embedding: Optional[List[float]],
            limit: int = 10,
            owner_id: Optional[str] = None,
            theme_id: Optional[str] = None
    ) -> List[Document]:
        """
        Search for similar documents using a vector embedding.

        This method implements vector similarity search using PostgreSQL's pgvector extension.
        It calculates cosine similarity between the provided embedding and document embeddings.

        Parameters
        ----------
        embedding : Optional[List[float]]
            The query embedding vector. If None, returns all documents sorted by creation date.
        limit : int
            Maximum number of results to return
        owner_id : Optional[str]
            Filter results by owner ID
        theme_id : Optional[str]
            Filter results by theme ID

        Returns
        -------
        List[Document]
            Documents sorted by similarity to the query embedding
        """
        try:
            # If no embedding provided, return most recent documents
            if embedding is None:
                query = select(Document).order_by(Document.created_at.desc())

                # Apply owner filter if provided
                if owner_id:
                    query = query.where(Document.owner_id == owner_id)

                # Apply theme filter if provided
                if theme_id:
                    query = query.join(
                        ThemeDocument,
                        Document.id == ThemeDocument.document_id
                    ).where(ThemeDocument.theme_id == theme_id)

                query = query.limit(limit)

                # Create a new transaction for this operation
                result = await self.db.execute(query)
                return result.scalars().all()

            # For vector similarity search
            from sqlalchemy import text
            from sqlalchemy.sql import column
            import numpy as np

            # Convert embedding to SQL-compatible array string
            embedding_str = str(embedding).replace('[', '{').replace(']', '}')

            # Build SQL query for vector similarity
            # This uses PostgreSQL's vector operators with the pgvector extension
            sql = """
            SELECT d.id, (d.embedding <=> :embedding) as similarity
            FROM documents d
            """

            params = {"embedding": embedding_str, "limit": limit}

            # Add theme join if needed
            if theme_id:
                sql += """
                JOIN theme_documents td ON d.id = td.document_id
                WHERE td.theme_id = :theme_id
                """
                params["theme_id"] = theme_id

                # Add owner filter if provided with theme
                if owner_id:
                    sql += " AND d.owner_id = :owner_id"
                    params["owner_id"] = owner_id
            elif owner_id:
                # Just owner filter without theme
                sql += " WHERE d.owner_id = :owner_id"
                params["owner_id"] = owner_id

            # Order by similarity and limit results
            sql += """
            ORDER BY similarity ASC
            LIMIT :limit
            """

            # Use transaction to ensure proper handling of database errors
                # Execute the query to get document IDs and their similarity scores
            result = await self.db.execute(text(sql), params)
            rows = result.all()

            if not rows:
                return []

            similarity_data = {row.id: 1.0 - min(1.0, float(row.similarity)) for row in rows}

            # Now fetch the actual document objects
            doc_ids = list(similarity_data.keys())
            query = select(Document).where(Document.id.in_(doc_ids))
            result = await self.db.execute(query)
            documents = result.scalars().all()

            # Attach similarity scores to the document objects
            for doc in documents:
                doc.similarity = similarity_data.get(doc.id, 0.0)

            # Sort by similarity score (highest first)
            documents.sort(key=lambda x: x.similarity, reverse=True)

            return documents

        except Exception as e:
            logger.error(f"Error in search_similar: {str(e)}", exc_info=True)
            # Fallback to basic filtering if vector search fails
            return await self._fallback_search(limit, owner_id, theme_id)

    async def _fallback_search(
            self,
            limit: int,
            owner_id: Optional[str] = None,
            theme_id: Optional[str] = None
    ) -> List[Document]:
        """
        Fallback method for basic document retrieval when vector search is unavailable.

        Returns
        -------
        List[Document]
            Latest documents matching the filters
        """
        try:
            # Use a fresh transaction for the fallback query
            async with self.db.begin() as transaction:
                query = select(Document).order_by(Document.created_at.desc())

                if owner_id:
                    query = query.where(Document.owner_id == owner_id)

                if theme_id:
                    query = query.join(
                        ThemeDocument,
                        Document.id == ThemeDocument.document_id
                    ).where(ThemeDocument.theme_id == theme_id)

                query = query.limit(limit)
                result = await self.db.execute(query)
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Error in _fallback_search: {str(e)}", exc_info=True)
            # If even the fallback fails, return an empty list
            return []
