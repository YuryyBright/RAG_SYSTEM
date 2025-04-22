from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union


class VectorIndexInterface(ABC):
    """Abstract interface for vector index implementations."""

    @abstractmethod
    async def add_vectors(self, vectors: List[List[float]], ids: List[str]) -> List[str]:
        pass

    @abstractmethod
    async def search(self, query_vector: List[float], top_k: int = 10, filter_dict: Optional[Dict[str, Any]] = None) -> \
    List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_vectors(self, ids: List[str]) -> int:
        pass

    @abstractmethod
    async def count_vectors(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        pass
