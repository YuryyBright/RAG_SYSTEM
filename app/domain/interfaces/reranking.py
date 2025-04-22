# app/core/interfaces/reranking.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class RerankingService(ABC):
    """Interface for document reranking services."""

    @abstractmethod
    async def rerank(self, query: str, documents: List[str], metadata: Optional[List[Dict[str, Any]]] = None,
               top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        pass
