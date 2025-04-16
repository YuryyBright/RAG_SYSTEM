from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import os
import numpy as np

from app.core.entities.document import Document
from app.core.interfaces.document_store import DocumentStoreInterface
from app.infrastructure.database.repository.document_repository import DocumentRepository
from core.services.embedding_service import EmbeddingService


class DocumentStore(DocumentStoreInterface):
    """
    Document store implementation that handles document storage, retrieval, and embedding operations.

    This class provides methods to:
    - Store documents with their embeddings
    - Retrieve documents by ID
    - Search for documents using vector similarity
    - Delete documents

    Attributes:
        document_repository: Repository for database operations
        embedding_service: Service for creating document embeddings
        storage_path: Path to store processed documents and metadata
    """

    def __init__(
            self,
            document_repository: DocumentRepository,
            embedding_service: EmbeddingService,
            storage_path: Path
    ):
        self.document_repository = document_repository
        self.embedding_service = embedding_service
        self.storage_path = storage_path

        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)

    async def save(self, document: Document) -> str:
        """
        Store a document with its embedding (Interface method).

        Args:
            document: Document entity to store

        Returns:
            str: ID of the stored document
        """
        return await self.store_document(document)

    async def store_document(self, document: Document) -> str:
        """
        Store a document with its embedding.

        Args:
            document: Document entity to store

        Returns:
            str: ID of the stored document
        """
        # Generate embedding if not already present
        if document.embedding is None:
            document.embedding = await self.embedding_service.get_embedding(document.content)

        # Save to database
        doc_id = await self.document_repository.create_document(
            content=document.content,
            embedding=document.embedding,
            owner_id=document.owner_id,
            file_id=document.file_id,
            theme_id=document.theme_id,
            metadata=document.metadata
        )

        # Save content to file system for faster retrieval
        self._save_document_to_disk(doc_id, document)

        return doc_id

    async def get(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by its ID (Interface method).

        Args:
            document_id: ID of the document to retrieve

        Returns:
            Optional[Document]: Document if found, None otherwise
        """
        return await self.get_document(document_id)

    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by its ID.

        Args:
            document_id: ID of the document to retrieve

        Returns:
            Optional[Document]: Document if found, None otherwise
        """
        # Try to get from disk cache first for performance
        document = self._load_document_from_disk(document_id)

        # Fall back to database if not in cache
        if not document:
            db_document = await self.document_repository.get_by_id(document_id)
            if db_document:
                document = Document(
                    id=db_document.id,
                    content=db_document.content,
                    embedding=db_document.embedding,
                    owner_id=db_document.owner_id,
                    metadata=self._extract_metadata(db_document),
                    created_at=db_document.created_at,
                    updated_at=db_document.updated_at
                )
                # Save to disk cache for future retrievals
                self._save_document_to_disk(document_id, document)

        return document

    async def get_documents(self, document_ids: List[str], owner_id, theme_id) -> List[Document]:
        """
        Get multiple documents by their IDs (Interface method).

        Args:
            document_ids: List of document IDs to retrieve
            owner_id: Owner ID
            theme_id: Theme ID

        Returns:
            List[Document]: List of found documents
        """
        # Try to get from disk cache first
        documents = []
        missing_ids = []

        # First try from disk cache
        for doc_id in document_ids:
            doc = self._load_document_from_disk(doc_id, owner_id, theme_id)
            if doc:
                documents.append(doc)
            else:
                missing_ids.append(doc_id)

        # Get any missing documents from database
        if missing_ids:
            # First, try with get_documents if the repository implements it
            db_documents = []
            try:
                db_documents = await self.document_repository.get_documents(missing_ids)
            except (AttributeError, NotImplementedError):
                # Fallback if get_documents is not implemented in repository
                for doc_id in missing_ids:
                    db_doc = await self.document_repository.get_by_id(doc_id)
                    if db_doc:
                        db_documents.append(db_doc)

            # Process found database documents
            for db_doc in db_documents:
                document = Document(
                    id=db_doc.id,
                    content=db_doc.content,
                    embedding=db_doc.embedding,
                    owner_id=db_doc.owner_id,
                    metadata=self._extract_metadata(db_doc),
                    created_at=db_doc.created_at,
                    updated_at=db_doc.updated_at
                )
                documents.append(document)
                # Save to disk cache for future retrievals
                self._save_document_to_disk(db_doc.id, document)

        return documents

    async def get_all(self, owner_id: Optional[str] = None) -> List[Document]:
        """
        Get all documents, optionally filtering by owner (Interface method).

        Args:
            owner_id: Optional filter for document owner

        Returns:
            List[Document]: List of documents
        """
        results = []

        # First try with get_all_documents if it exists
        try:
            results = await self.document_repository.get_all_documents(owner_id=owner_id)
        except (AttributeError, NotImplementedError):
            # Fallback to search without query if repository doesn't have get_all_documents
            try:
                results = await self.document_repository.search_similar(
                    embedding=None,  # Some repositories might handle None as "get all"
                    limit=1000,  # Reasonable limit to prevent excessive data retrieval
                    owner_id=owner_id
                )
            except (AttributeError, NotImplementedError):
                # If neither method is implemented, log it (or handle as appropriate)
                return []

        documents = []
        for result in results:
            document = Document(
                id=result.id,
                content=result.content,
                embedding=result.embedding,
                owner_id=result.owner_id,
                metadata=self._extract_metadata(result),
                created_at=result.created_at,
                updated_at=result.updated_at
            )
            documents.append(document)
            # Cache the document for future use
            self._save_document_to_disk(result.id, document)

        return documents

    async def search_documents(
            self,
            query: str,
            limit: int = 5,
            owner_id: Optional[str] = None
    ) -> List[Document]:
        """
        Search for documents using vector similarity.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            owner_id: Optional filter for document owner

        Returns:
            List[Document]: List of matching documents
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_text(query)

        # Search database
        results = await self.document_repository.search_similar(
            embedding=query_embedding,
            limit=limit,
            owner_id=owner_id
        )

        # Convert to Document entities
        documents = []
        for result in results:
            document = Document(
                id=result.id,
                content=result.content,
                embedding=result.embedding,
                owner_id=result.owner_id,
                metadata=self._extract_metadata(result),
                created_at=result.created_at,
                updated_at=result.updated_at
            )
            documents.append(document)

        return documents

    async def delete(self, document_id: str) -> bool:
        """
        Delete a document by its ID (Interface method).

        Args:
            document_id: ID of the document to delete

        Returns:
            bool: True if deleted, False if not found
        """
        return await self.delete_document(document_id)

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document by its ID.

        Args:
            document_id: ID of the document to delete

        Returns:
            bool: True if deleted, False if not found
        """
        # Delete from database
        deleted = await self.document_repository.delete_document(document_id)

        # Delete from disk cache if exists
        if deleted:
            self._delete_document_from_disk(document_id)

        return deleted

    async def update_document(self, document: Document) -> bool:
        """
        Update an existing document.

        Args:
            document: Document entity with updated fields

        Returns:
            bool: True if updated, False if not found
        """
        # Update embedding if content changed
        if document.embedding is None:
            document.embedding = await self.embedding_service.embed_text(document.content)

        # Update in database
        updated = await self.document_repository.update_document(
            document_id=document.id,
            content=document.content,
            embedding=document.embedding,
            metadata=document.metadata
        )

        # Update disk cache if successful
        if updated:
            self._save_document_to_disk(document.id, document)

        return updated

    async def count_documents(self, filter_criteria: Dict[str, Any] = None) -> int:
        """
        Count documents matching the filter criteria.

        Args:
            filter_criteria: Dictionary of criteria to filter documents

        Returns:
            int: Count of matching documents
        """
        try:
            return await self.document_repository.count_documents(filter_criteria)
        except (AttributeError, NotImplementedError):
            # Fallback to counting manually if the repository doesn't implement count_documents
            try:
                # Get all documents and filter manually
                all_docs = await self.get_all()

                if not filter_criteria:
                    return len(all_docs)

                # Filter documents based on criteria
                count = 0
                for doc in all_docs:
                    matches = True
                    for key, value in filter_criteria.items():
                        if key == "owner_id" and doc.owner_id != value:
                            matches = False
                            break
                        if key in doc.metadata and doc.metadata[key] != value:
                            matches = False
                            break
                    if matches:
                        count += 1
                return count
            except Exception:
                # If all else fails, return 0
                return 0

    def _save_document_to_disk(self, document_id: str, document: Document) -> None:
        """Save document to disk for faster retrieval."""

        # Construct file path
        file_path = self.storage_path / document.owner_id / document.theme_id / f"{document.id}.json"

        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert document to serializable dict
        doc_dict = {
            "id": document.id,
            "content": document.content,
            "owner_id": document.owner_id,
            "metadata": document.metadata,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "has_embedding": document.embedding is not None
        }

        # Write JSON file
        with open(file_path, "w") as f:
            json.dump(doc_dict, f)

        # Store embedding separately if present
        if document.embedding is not None:
            embedding_path = self.storage_path / document.owner_id / document.theme_id / f"{document.id}.embedding"
            embedding_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
            with open(embedding_path, "wb") as f:
                np.save(f, np.array(document.embedding))

    def _load_document_from_disk(self, document_id: str, owner_id: str, theme_id: str) -> Document:
        """Load document from disk."""

        # Construct file path
        file_path = Path(self.storage_path) / owner_id / theme_id / f"{document_id}.json"

        # Check if file exists
        if not file_path.exists():
            return None

        # Load document data
        with open(file_path, "r") as f:
            doc_dict = json.load(f)

        # Load embedding if available
        embedding = None
        if doc_dict.get("has_embedding", False):
            embedding_path = Path(self.storage_path) / owner_id / theme_id / f"{document_id}.embedding"
            if embedding_path.exists():
                with open(embedding_path, "rb") as f:
                    embedding = np.load(f).tolist()

        # Create Document object
        document = Document(
            id=doc_dict["id"],
            content=doc_dict["content"],
            owner_id=doc_dict["owner_id"],
            metadata=doc_dict["metadata"],
            embedding=embedding
        )

        if doc_dict.get("created_at"):
            from datetime import datetime
            document.created_at = datetime.fromisoformat(doc_dict["created_at"])

        if doc_dict.get("updated_at"):
            from datetime import datetime
            document.updated_at = datetime.fromisoformat(doc_dict["updated_at"])

        return document

    def _delete_document_from_disk(self, document_id: str) -> None:
        """Delete document from disk cache."""
        file_path = self.storage_path / f"{document_id}.json"
        embedding_path = self.storage_path / f"{document_id}.embedding"

        if file_path.exists():
            os.remove(file_path)

        if embedding_path.exists():
            os.remove(embedding_path)

    def _extract_metadata(self, db_document) -> Dict[str, Any]:
        """Extract metadata from database document model."""
        # First check if document already has metadata as a dictionary
        if hasattr(db_document, "metadata") and isinstance(db_document.metadata, dict):
            return db_document.metadata.copy()

        # Otherwise try to extract from document_metadata list of key-value pairs
        metadata = {}
        try:
            for meta_item in getattr(db_document, "document_metadata", []):
                metadata[meta_item.key] = meta_item.value
        except (AttributeError, TypeError):
            # If document doesn't have expected structure, return empty dict
            pass

        return metadata