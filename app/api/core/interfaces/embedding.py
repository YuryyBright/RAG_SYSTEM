from abc import ABC, abstractmethod
from typing import List
from api.core.entities.document import Document


class EmbeddingInterface(ABC):
    """
    Interface for embedding models.

    This interface defines the methods required for embedding models to process
    documents and queries. Implementations of this interface should provide
    functionality to generate embeddings for both documents and query strings.
    """

    @abstractmethod
    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents.

        This method takes a list of `Document` objects, processes their content,
        and generates embeddings for each document. The embeddings are then
        added to the `embedding` attribute of the respective `Document` objects.

        Args:
            documents (List[Document]): A list of `Document` objects to be embedded.

        Returns:
            List[Document]: The list of `Document` objects with their `embedding`
            attributes populated.
        """
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a query string.

        This method takes a query string as input and generates a vector
        representation (embedding) for it. The embedding can be used for
        similarity searches or other tasks.

        Args:
            query (str): The query string to be embedded.

        Returns:
            List[float]: A list of floats representing the embedding of the query.
        """
        pass