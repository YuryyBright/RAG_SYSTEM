# app/core/interfaces/indexing.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from api.core.entities.document import Document

class IndexInterface(ABC):
    """
    Interface for vector index implementations.

    This interface defines the methods required for managing a vector index of documents.
    Implementations of this interface should provide functionality to add, search, delete,
    save, and load documents in the index.

    Methods
    -------
    add_documents(documents: List[Document]) -> None
        Asynchronously adds a list of documents to the index.
    search(query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]
        Asynchronously searches the index for documents similar to the query embedding.
    delete_document(doc_id: str) -> None
        Asynchronously deletes a document from the index by its ID.
    save_index(path: str) -> None
        Asynchronously saves the current state of the index to disk.
    load_index(path: str) -> None
        Asynchronously loads the index state from disk.
    """

    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the index.

        Parameters
        ----------
        documents : List[Document]
            A list of `Document` objects to be added to the index.
        """
        pass

    @abstractmethod
    async def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the index for similar documents to the query embedding.

        Parameters
        ----------
        query_embedding : List[float]
            A list of floats representing the embedding of the query.
        k : int, optional
            The number of top similar documents to return (default is 5).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries containing the IDs and similarity scores of the top similar documents.
        """
        pass

    @abstractmethod
    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from the index.

        Parameters
        ----------
        doc_id : str
            The unique identifier of the document to be deleted.
        """
        pass

    @abstractmethod
    async def save_index(self, path: str) -> None:
        """
        Save the index to disk.

        Parameters
        ----------
        path : str
            The file path where the index should be saved.
        """
        pass

    @abstractmethod
    async def load_index(self, path: str) -> None:
        """
        Load the index from disk.

        Parameters
        ----------
        path : str
            The file path from where the index should be loaded.
        """
        pass