# app/adapters/storage/document_store.py
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import os
import uuid

from app.core.entities.document import Document
from app.core.interfaces.document_store import DocumentStoreInterface
from app.core.interfaces.embedding import EmbeddingInterface
from app.infrastructure.database.repository.document_repository import DocumentRepository


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
            embedding_service: EmbeddingInterface,
            storage_path: Path
    ):
        self.document_repository = document_repository
        self.embedding_service = embedding_service
        self.storage_path = storage_path

        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)

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
            document.embedding = await self.embedding_service.embed_text(document.content)

        # Save to database
        doc_id = await self.document_repository.create_document(
            content=document.content,
            embedding=document.embedding,
            owner_id=document.owner_id,
            metadata=document.metadata
        )

        # Save content to file system for faster retrieval
        self._save_document_to_disk(doc_id, document)

        return doc_id

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
            db_document = await self.document_repository.get_document(document_id)
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

    def _save_document_to_disk(self, document_id: str, document: Document) -> None:
        """Save document to disk for faster retrieval."""
        file_path = self.storage_path / f"{document_id}.json"

        # Convert document to serializable dict
        doc_dict = {
            "id": document.id,
            "content": document.content,
            "owner_id": document.owner_id,
            "metadata": document.metadata,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,

            # Store embedding separately or skip if very large
            "has_embedding": document.embedding is not None
        }

        with open(file_path, "w") as f:
            json.dump(doc_dict, f)

        # Store embedding separately if present (can be large)
        if document.embedding is not None:
            embedding_path = self.storage_path / f"{document_id}.embedding"
            with open(embedding_path, "wb") as f:
                f.write(document.embedding)

    def _load_document_from_disk(self, document_id: str) -> Optional[Document]:
        """Load document from disk cache."""
        file_path = self.storage_path / f"{document_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                doc_dict = json.load(f)

            # Load embedding if available
            embedding = None
            embedding_path = self.storage_path / f"{document_id}.embedding"
            if embedding_path.exists() and doc_dict.get("has_embedding", False):
                with open(embedding_path, "rb") as f:
                    embedding = f.read()

            return Document(
                id=doc_dict["id"],
                content=doc_dict["content"],
                embedding=embedding,
                owner_id=doc_dict["owner_id"],
                metadata=doc_dict.get("metadata", {}),
                created_at=doc_dict["created_at"],
                updated_at=doc_dict["updated_at"]
            )
        except Exception:
            # If there's any error reading the file, return None
            return None

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
        metadata = {}
        for meta_item in getattr(db_document, "document_metadata", []):
            metadata[meta_item.key] = meta_item.value
        return metadata