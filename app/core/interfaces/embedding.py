# core/interfaces/embedding.py
from abc import ABC, abstractmethod
from typing import List
from core.entities.document import Document


class EmbeddingInterface(ABC):
    """
    Interface for embedding services.

    This abstract class defines the methods that any embedding model
    implementation must provide to work with the system.
    """

    @abstractmethod
    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents.

        Args:
            documents (List[Document]): A list of Document objects to be embedded.

        Returns:
            List[Document]: The list of Document objects with their embedding attributes populated.
        """
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a query string.

        Args:
            query (str): The query string to be embedded.

        Returns:
            List[float]: A list of floats representing the embedding of the query.
        """
        pass