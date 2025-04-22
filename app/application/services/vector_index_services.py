# core/services/vector_index_services.py
from typing import List, Dict, Any, Optional
import numpy as np


class VectorIndexService:
    """
    Service for managing vector indices, providing storage and similarity search capabilities
    for document embeddings.
    """

    def __init__(self, index_name: str, dimensions: int = 1536):
        """
        Initialize the vector index service.

        Args:
            index_name: Name of the vector index
            dimensions: Dimensionality of the vectors to be stored
        """
        self.index_name = index_name
        self.dimensions = dimensions
        self.vectors = {}  # Simple in-memory storage for vectors
        self.metadata = {}  # Metadata associated with vectors

    async def add_vectors(self, vectors: List[Any], ids: List[str], metadata: Optional[List[Dict[str, Any]]] = None) -> \
    List[str]:
        """
        Add vectors to the index.

        Args:
            vectors: List of vector embeddings
            ids: List of IDs to associate with the vectors
            metadata: Optional list of metadata dictionaries for each vector

        Returns:
            List of vector IDs that were added
        """
        if len(vectors) != len(ids):
            raise ValueError("Length of vectors and ids must match")

        if metadata and len(metadata) != len(ids):
            raise ValueError("Length of metadata and ids must match")

        added_ids = []

        for i, (vector, id) in enumerate(zip(vectors, ids)):
            # Store the vector
            self.vectors[id] = vector

            # Store metadata if provided
            if metadata:
                self.metadata[id] = metadata[i]
            else:
                self.metadata[id] = {}

            added_ids.append(id)

        return added_ids

    async def search_similar(self, query_vector: Any, limit: int = 5,
                             filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for vectors similar to the query vector.

        Args:
            query_vector: Vector to search for
            limit: Maximum number of results to return
            filter_criteria: Optional criteria to filter results

        Returns:
            List of dictionaries containing vector ID, score, and metadata
        """
        if not self.vectors:
            return []

        # Convert to numpy for easier calculation
        query_np = np.array(query_vector)

        results = []

        for id, vector in self.vectors.items():
            # Skip if doesn't match filter criteria
            if filter_criteria and not self._matches_filter(id, filter_criteria):
                continue

            # Calculate cosine similarity
            vector_np = np.array(vector)
            similarity = np.dot(query_np, vector_np) / (np.linalg.norm(query_np) * np.linalg.norm(vector_np))

            results.append({
                "id": id,
                "score": float(similarity),
                "metadata": self.metadata.get(id, {})
            })

        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)

        # Return top results
        return results[:limit]

    async def delete_vectors(self, ids: List[str]) -> int:
        """
        Delete vectors from the index.

        Args:
            ids: List of vector IDs to delete

        Returns:
            Number of vectors deleted
        """
        deleted_count = 0

        for id in ids:
            if id in self.vectors:
                del self.vectors[id]
                if id in self.metadata:
                    del self.metadata[id]
                deleted_count += 1

        return deleted_count

    async def count_vectors(self, filter_criteria: Optional[Dict[str, Any]] = None) -> int:
        """
        Count vectors in the index, optionally filtered by criteria.

        Args:
            filter_criteria: Optional criteria to filter vectors

        Returns:
            Count of matching vectors
        """
        if not filter_criteria:
            return len(self.vectors)

        count = 0
        for id in self.vectors:
            if self._matches_filter(id, filter_criteria):
                count += 1

        return count

    def get_index_type(self) -> str:
        """
        Get the type of vector index.

        Returns:
            String describing the vector index type
        """
        return "in-memory"

    def get_dimensions(self) -> int:
        """
        Get the dimensionality of vectors in the index.

        Returns:
            Number of dimensions for vectors
        """
        return self.dimensions

    def _matches_filter(self, vector_id: str, filter_criteria: Dict[str, Any]) -> bool:
        """
        Check if a vector matches the filter criteria.

        Args:
            vector_id: ID of the vector to check
            filter_criteria: Dictionary of filter criteria

        Returns:
            True if the vector matches the criteria, False otherwise
        """
        if vector_id not in self.metadata:
            return False

        vector_metadata = self.metadata[vector_id]

        for key, value in filter_criteria.items():
            if key not in vector_metadata or vector_metadata[key] != value:
                return False

        return True