# app/modules/reranking/bm25_reranker.py
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from domain.interfaces.reranking import RerankingService


class BM25Reranker(RerankingService):
    """
    Reranker using BM25 algorithm for text relevance scoring.
    """

    def rerank(
            self,
            query: str,
            documents: List[str],
            metadata: Optional[List[Dict[str, Any]]] = None,
            top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using BM25 algorithm.

        Parameters
        ----------
        query : str
            The query text
        documents : List[str]
            List of document texts to rerank
        metadata : Optional[List[Dict[str, Any]]], optional
            List of metadata for each document, by default None
        top_k : Optional[int], optional
            Number of top results to return, by default None

        Returns
        -------
        List[Dict[str, Any]]
            Reranked documents with scores
        """
        if not documents:
            return []

        # Tokenize documents and query
        tokenized_docs = [doc.lower().split() for doc in documents]
        tokenized_query = query.lower().split()

        # Create BM25 model
        bm25 = BM25Okapi(tokenized_docs)

        # Get scores
        scores = bm25.get_scores(tokenized_query)

        # Create result with document, score, and metadata
        results = []
        for i, (doc, score) in enumerate(zip(documents, scores)):
            result = {
                "content": doc,
                "score": float(score),
                "metadata": metadata[i] if metadata else {}
            }
            results.append(result)

        # Sort by score in descending order
        results = sorted(results, key=lambda x: x["score"], reverse=True)

        # Limit to top_k if specified
        if top_k and top_k > 0:
            results = results[:top_k]

        return results