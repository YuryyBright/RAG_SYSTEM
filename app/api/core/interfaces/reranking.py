from abc import ABC, abstractmethod
from typing import List, Dict, Any

class RerankerInterface(ABC):
    """
    Interface for reranking retrieved documents.

    This interface defines the contract for reranking a list of documents based on their relevance
    to a given query. Implementations of this interface should provide functionality to rerank
    documents and return the top-k most relevant documents.

    Methods
    -------
    rerank(query: str, documents: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]
        Asynchronously reranks the provided documents based on their relevance to the query.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to the query.

        Parameters
        ----------
        query : str
            The query string to evaluate the relevance of the documents.
        documents : List[Dict[str, Any]]
            A list of dictionaries, each representing a document with its attributes.
        top_k : int, optional
            The number of top relevant documents to return (default is 3).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries representing the top-k most relevant documents.
        """
        pass