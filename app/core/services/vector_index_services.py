# app/core/services/vector_index_services.py
from typing import List, Dict, Any, Optional, Union
import numpy as np
import uuid

from core.interfaces.vector_index import VectorIndexInterface
from utils.logger_util import get_logger

logger = get_logger(__name__)





class VectorIndex(VectorIndexInterface):
    """Service for storing and searching vector embeddings."""

    def __init__(self, dimensions: int = 768, index_type: str = "hnsw"):
        """
        Initialize the vector index.

        Args:
            dimensions: Dimensionality of the vectors
            index_type: Type of index (e.g., "hnsw", "flat")
        """
        self.dimensions = dimensions
        self.index_type = index_type

        # In a real implementation, this would initialize the vector database
        # For demonstration, we'll use a simple in-memory store
        self._vectors = {}  # id -> vector
        self._metadata = {}  # id -> metadata

        logger.info(f"Initialized VectorIndex ({index_type}) with {dimensions} dimensions")

    async def add_vectors(self, vectors: List[List[float]], ids: Optional[List[str]] = None) -> List[str]:
        """
        Add vectors to the index.

        Args:
            vectors: List of embedding vectors
            ids: Optional list of IDs corresponding to the vectors

        Returns:
            List of IDs of the added vectors
        """
        if not vectors:
            return []

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        elif len(ids) != len(vectors):
            raise ValueError("Length of ids must match length of vectors")

        # Add vectors to store
        for vec_id, vector in zip(ids, vectors):
            self._vectors[vec_id] = vector
            if vec_id not in self._metadata:
                self._metadata[vec_id] = {}

        logger.debug(f"Added {len(vectors)} vectors to index")
        return ids

    async def search(self, query_vector: List[float], top_k: int = 10, filter_dict: Optional[Dict[str, Any]] = None) -> \
    List[Dict[str, Any]]:
        """
        Search for vectors similar to query_vector.

        Args:
            query_vector: Vector to search for
            top_k: Number of results to return
            filter_dict: Optional dictionary of metadata filters

        Returns:
            List of search results with document IDs and scores
        """
        if not self._vectors:
            return []

        # Filter by metadata if filter_dict is provided
        candidate_ids = self._vectors.keys()
        if filter_dict:
            candidate_ids = [
                vec_id for vec_id in candidate_ids
                if self._matches_filter(self._metadata.get(vec_id, {}), filter_dict)
            ]

        # Calculate similarities
        query_np = np.array(query_vector)
        similarities = []

        for vec_id in candidate_ids:
            vector = self._vectors[vec_id]
            # Calculate cosine similarity
            vector_np = np.array(vector)
            dot_product = np.dot(query_np, vector_np)
            magnitude_product = np.linalg.norm(query_np) * np.linalg.norm(vector_np)
            similarity = dot_product / magnitude_product if magnitude_product > 0 else 0

            similarities.append((vec_id, similarity))

        # Sort by similarity (descending) and take top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        results = [
            {"id": vec_id, "score": float(score), "metadata": self._metadata.get(vec_id, {})}
            for vec_id, score in similarities[:top_k]
        ]

        logger.debug(f"Search returned {len(results)} results")
        return results

    async def delete_vectors(self, ids: List[str]) -> int:
        """
        Delete vectors from the index.

        Args:
            ids: List of IDs to delete

        Returns:
            Number of vectors deleted
        """
        deleted_count = 0
        for vec_id in ids:
            if vec_id in self._vectors:
                del self._vectors[vec_id]
                if vec_id in self._metadata:
                    del self._metadata[vec_id]
                deleted_count += 1

        logger.debug(f"Deleted {deleted_count} vectors from index")
        return deleted_count

    async def count_vectors(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        Count vectors in the index.

        Args:
            filter_dict: Optional dictionary of metadata filters

        Returns:
            Number of vectors matching the filter
        """
        if not filter_dict:
            return len(self._vectors)

        # Count vectors that match the filter
        count = sum(
            1 for vec_id in self._vectors
            if self._matches_filter(self._metadata.get(vec_id, {}), filter_dict)
        )

        return count

    async def update_metadata(self, vec_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a vector.

        Args:
            vec_id: ID of the vector
            metadata: Metadata to update

        Returns:
            True if successful, False if vector not found
        """
        if vec_id not in self._vectors:
            return False

        if vec_id not in self._metadata:
            self._metadata[vec_id] = {}

        self._metadata[vec_id].update(metadata)
        return True

    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """
        Check if metadata matches filter criteria.

        Args:
            metadata: Metadata dictionary to check
            filter_dict: Filter criteria

        Returns:
            True if metadata matches filter, False otherwise
        """
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True

    def get_index_type(self) -> str:
        """
        Get the type of index.

        Returns:
            Type of the index
        """
        return self.index_type

    def get_dimensions(self) -> int:
        """
        Get the dimensionality of the vectors.

        Returns:
            Number of dimensions
        """
        return self.dimensions