from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
class VectorIndexInterface(ABC):
    """Abstract interface for vector index implementations."""

    @abstractmethod
    async def add_vectors(self, vectors: List[List[float]], ids: List[str]) -> List[str]:
        """
        Add vectors to the index.

        Args:
            vectors: List of embedding vectors
            ids: List of IDs corresponding to the vectors

        Returns:
            List of IDs of the added vectors
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def delete_vectors(self, ids: List[str]) -> int:
        """
        Delete vectors from the index.

        Args:
            ids: List of IDs to delete

        Returns:
            Number of vectors deleted
        """
        pass

    @abstractmethod
    async def count_vectors(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        Count vectors in the index.

        Args:
            filter_dict: Optional dictionary of metadata filters

        Returns:
            Number of vectors matching the filter
        """
        pass