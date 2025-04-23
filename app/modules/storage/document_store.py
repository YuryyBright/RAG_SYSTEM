from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import os
import numpy as np

from domain.entities.document import Document
from domain.interfaces.document_store import DocumentStoreInterface

from domain.interfaces.embedding import EmbeddingInterface
from infrastructure.repositories.document_repository import DocumentRepository
from utils.logger_util import get_logger


class DocumentStore(DocumentStoreInterface):
    """
    Document store implementation that handles document storage, retrieval, and embedding operations.
    """

    def __init__(
            self,
            document_repository: DocumentRepository,
            embedding_service: EmbeddingInterface,
            storage_path: Path
    ):
        self.document_repository = document_repository
        self.embedding_service = embedding_service
        self.storage_path = Path(storage_path)  # Ensure it's a Path object
        self.logger = get_logger(__name__)

        # Create storage directory if it doesn't exist
        try:
            os.makedirs(self.storage_path, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create storage directory: {str(e)}", exc_info=True)

    async def semantic_search(
            self,
            query_embedding: List[float],
            limit: int = 5,
            owner_id: Optional[str] = None,
            theme_id: Optional[str] = None,
            threshold: float = 0.7,
            metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform semantic search using a pre-computed query embedding.

        Args:
            query_embedding: The pre-computed query embedding vector
            limit: Maximum number of results to return
            owner_id: Optional filter for document owner
            theme_id: Optional filter for document theme
            threshold: Minimum similarity score (0-1) for results
            metadata_filters: Optional dictionary of metadata key-value pairs to filter on

        Returns:
            List[Document]: List of matching Document objects with similarity scores
        """
        try:
            # Search documents in repository
            results = await self.document_repository.search_similar(
                embedding=query_embedding,
                limit=limit * 2,  # Get more than needed to allow for filtering
                owner_id=owner_id,
                theme_id=theme_id
            )

            # Convert to Document entities with similarity scores
            documents = []
            for result in results:
                # Extract similarity score if available in result
                similarity = getattr(result, 'similarity', None)

                # If similarity not provided by repository, calculate it
                if similarity is None and result.embedding is not None:
                    similarity = self._calculate_similarity(query_embedding, result.embedding)

                # Skip results below threshold
                if similarity is None or similarity < threshold:
                    continue

                # Create document object
                document = Document(
                    id=result.id,
                    content=result.content,
                    embedding=result.embedding,
                    owner_id=result.owner_id,
                    theme_id=getattr(result, 'theme_id', theme_id),
                    metadata=self._extract_metadata(result),
                    created_at=result.created_at.isoformat(),
                    updated_at=result.updated_at.isoformat()
                )
                document.score = similarity  # Add score to document

                # Apply metadata filters if provided
                if metadata_filters and not self._matches_metadata_filters(document, metadata_filters):
                    continue

                documents.append(document)

            # Sort by similarity score (highest first)
            documents.sort(key=lambda x: getattr(x, 'score', 0), reverse=True)

            # Limit results
            return documents[:limit]
        except Exception as e:
            self.logger.error(f"Error in semantic search: {str(e)}", exc_info=True)
            return []

    def _save_document_to_disk(self, document_id: str, document: Document) -> None:
        """Save document to disk for faster retrieval."""
        try:
            # Construct file path
            file_path = self.storage_path / document.owner_id / document.theme_id / f"{document_id}.json"

            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert document to serializable dict
            doc_dict = {
                "id": document.id,
                "content": document.content,
                "owner_id": document.owner_id,
                "metadata": document.metadata,
                "created_at": document.created_at.isoformat() if hasattr(document.created_at, 'isoformat') else None,
                "updated_at": document.updated_at.isoformat() if hasattr(document.updated_at, 'isoformat') else None,
                "has_embedding": document.embedding is not None
            }

            # Write JSON file
            with open(file_path, "w") as f:
                json.dump(doc_dict, f)

            # Store embedding separately if present
            if document.embedding is not None:
                embedding_path = self.storage_path / document.owner_id / document.theme_id / f"{document_id}.embedding.npy"
                np.save(embedding_path, np.array(document.embedding))
        except Exception as e:
            self.logger.error(f"Error saving document to disk: {str(e)}", exc_info=True)

    def _load_document_from_disk(self, document_id: str, owner_id: str, theme_id: str) -> Optional[Document]:
        """Load document from disk."""
        try:
            # Traverse all directories if owner_id or theme_id is not provided
            base_path = self.storage_path

            if owner_id:
                base_path = base_path / owner_id
            else:
                owner_dirs = list(base_path.glob("*"))
                if not owner_dirs:
                    return None
                base_path = owner_dirs[0]

            if theme_id:
                base_path = base_path / theme_id
            else:
                theme_dirs = list(base_path.glob("*"))
                if not theme_dirs:
                    return None
                base_path = theme_dirs[0]

            file_path = base_path / f"{document_id}.json"

            if not file_path.exists():
                return None

            with open(file_path, "r") as f:
                doc_dict = json.load(f)

            embedding = None
            if doc_dict.get("has_embedding", False):
                embedding_path = file_path.with_suffix(".embedding.npy")
                if embedding_path.exists():
                    embedding = np.load(embedding_path).tolist()

            from datetime import datetime
            document = Document(
                id=doc_dict["id"],
                content=doc_dict["content"],
                owner_id=doc_dict["owner_id"],
                metadata=doc_dict.get("metadata", {}),
                embedding=embedding,
                theme_id=theme_id or base_path.name,
                created_at=datetime.fromisoformat(doc_dict["created_at"]) if doc_dict.get("created_at") else None,
                updated_at=datetime.fromisoformat(doc_dict["updated_at"]) if doc_dict.get("updated_at") else None
            )

            return document
        except Exception as e:
            self.logger.error(f"Error loading document from disk: {str(e)}", exc_info=True)
            return None

    async def store_document(self, document: Document) -> str:
        """
        Store a document with its embedding, link it to a theme if theme_id provided.

        Args:
            document: Document entity to store

        Returns:
            str: ID of the stored document
        """

        # Generate embedding if not already present
        if document.embedding is None:
            document.embedding = await self.embedding_service.get_embedding(document.content)

        # Save Document to database
        doc_id = await self.document_repository.create_document(
            content=document.content,
            embedding=document.embedding,
            owner_id=document.owner_id,
            file_id=document.file_id,
            theme_id=document.theme_id,
            metadata=document.metadata
        )
        if document.theme_id:
            await self.document_repository.create_theme_document_link(
                theme_id=document.theme_id,
                document_id=doc_id
            )

        # Save content to file system for faster retrieval
        self._save_document_to_disk(doc_id, document)

        return doc_id

    async def get(self, document_id: str, owner_id: str, theme_id: str) -> Optional[Document]:
        """
        Retrieve a document by its ID (Interface method).

        Args:
            document_id: ID of the document to retrieve
            owner_id: ID of the owner of the document
            theme_id: ID of the theme of the document

        Returns:
            Optional[Document]: Document if found, None otherwise
        """
        return await self.get_document(document_id, owner_id, theme_id)

    async def get_document(self, document_id: str, owner_id: str, theme_id: str) -> Optional[Document]:
        """
        Retrieve a document by its ID.

        Args:
            document_id: ID of the document to retrieve
            owner_id: ID of the owner of the document to retrieve
            theme_id: ID of the theme of the document to retrieve

        Returns:
            Optional[Document]: Document if found, None otherwise
        """
        # Try to get from disk cache first for performance
        document = self._load_document_from_disk(document_id,owner_id, theme_id)

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
                    created_at=db_document.created_at.isoformat(),
                    updated_at=db_document.updated_at.isoformat()
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
                    created_at=db_doc.created_at.isoformat(),
                    updated_at=db_doc.updated_at.isoformat()
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
                created_at=result.created_at.isoformat(),
                updated_at=result.updated_at.isoformat()
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
                created_at=result.created_at.isoformat(),
                updated_at=result.updated_at.isoformat()
            )
            documents.append(document)

        return documents

    async def delete(self, document_id: str, owner_id: str, theme_id: str) -> bool:
        """
        Delete a document by its ID (Interface method).

        Args:
            document_id: ID of the document to delete
            owner_id
            theme_id

        Returns:
            bool: True if deleted, False if not found
        """
        return await self.delete_document(document_id, owner_id, theme_id)

    async def delete_document(self, document_id: str, owner_id: str, theme_id: str) -> bool:
        """
        Delete a document by its ID.

        Args:
            document_id: ID of the document to delete
            owner_id:
            theme_id:


        Returns:
            bool: True if deleted, False if not found
        """
        # Delete from database
        deleted = await self.document_repository.delete_document(document_id)

        # Delete from disk cache if exists
        if deleted:
            self._delete_document_from_disk(document_id,owner_id, theme_id)

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

    def _delete_document_from_disk(self, document_id: str, owner_id: str, theme_id: str) -> None:
        """Delete document from disk cache."""
        file_path = Path(self.storage_path) / owner_id / theme_id / f"{document_id}.json"
        embedding_path = Path(self.storage_path) / owner_id / theme_id / f"{document_id}.embedding"

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



    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Cosine similarity score (0-1)
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        # Avoid division by zero
        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _matches_metadata_filters(self, document: Document, filters: Dict[str, Any]) -> bool:
        """
        Check if document metadata matches all provided filters.

        Args:
            document: Document to check
            filters: Dictionary of metadata key-value pairs to match

        Returns:
            bool: True if document matches all filters
        """
        # If document has no metadata or filters is empty, return False
        if not document.metadata:
            return False

        # Check if all filters match
        for key, value in filters.items():
            # Handle special case for list values (any match)
            if isinstance(value, list):
                if key not in document.metadata or document.metadata[key] not in value:
                    return False
            # Standard exact match
            elif key not in document.metadata or document.metadata[key] != value:
                return False

        return True
