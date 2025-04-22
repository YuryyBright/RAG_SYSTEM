# app/core/interfaces/reranking.py
from typing import List, Optional

class RerankingService:
    """
    Interface for reranking services that can reorder retrieved documents
    based on their relevance to a query.

    Methods:
        rerank: Reranks documents based on relevance to a query.
    """

    async def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_k: Optional[int] = None
    ) -> List[int]:
        """
        Reranks documents based on their relevance to the query.

        Args:
            query: The query text.
            documents: List of document contents to rerank.
            top_k: The number of top documents to return.

        Returns:
            List of indices of the original documents list, ordered by relevance.
        """
        raise NotImplementedError