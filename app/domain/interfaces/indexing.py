# app/core/interfaces/indexing.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from domain.entities.document import Document


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
    add_vectors(vectors: List[List[float]], document_ids: List[str],
                contents: List[str], metadata: List[Dict]) -> None
        Asynchronously adds raw vectors with metadata directly to the index.
    """

    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> None:
        pass

    @abstractmethod
    async def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_document(self, doc_id: str) -> None:
        pass

    @abstractmethod
    async def save_index(self, path: str) -> None:
        pass

    @abstractmethod
    async def load_index(self, path: str) -> None:
        pass

    @abstractmethod
    async def add_vectors(self, vectors: List[List[float]], document_ids: List[str], contents: List[str],
                          metadata: List[Dict]) -> None:
        pass
