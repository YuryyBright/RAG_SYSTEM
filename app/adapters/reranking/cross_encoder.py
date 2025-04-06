import httpx
from typing import List, Dict, Any
from api.core.interfaces.reranking import RerankerInterface
from app.config import settings

class CrossEncoderReranker(RerankerInterface):
    """
    Implementation of the RerankerInterface using a cross-encoder model.

    This class provides methods to rerank documents based on their relevance to a given query
    using a specified cross-encoder model through an external API.

    Attributes
    ----------
    model_name : str
        The name of the model to use for reranking.
    api_url : str
        The URL of the reranker API.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.api_url = settings.RERANKER_API_URL

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on their relevance to the query.

        Parameters
        ----------
        query : str
            The user's query.
        documents : List[Dict[str, Any]]
            A list of dictionaries representing the documents to be reranked.
        top_k : int, optional
            The number of top documents to return after reranking (default is 3).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries containing the reranked documents with their new scores.
        """
        if not documents:
            return []

        # Prepare pairs for reranking
        pairs = [
            [query, doc.get("content", "")]
            for doc in documents
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/rerank",
                json={
                    "model": self.model_name,
                    "pairs": pairs,
                }
            )
            response.raise_for_status()
            data = response.json()

            # Get scores from response
            scores = data["scores"]

            # Combine documents with new scores
            scored_docs = []
            for i, doc in enumerate(documents):
                doc_copy = doc.copy()
                doc_copy["score"] = float(scores[i])
                scored_docs.append(doc_copy)

            # Sort by score in descending order and get top_k
            scored_docs.sort(key=lambda x: x["score"], reverse=True)
            return scored_docs[:top_k]