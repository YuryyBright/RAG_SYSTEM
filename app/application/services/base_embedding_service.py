# core/services/base_embedding_service.py
from typing import List

from domain.entities.document import Document
from domain.interfaces.embedding import EmbeddingInterface
from utils.logger_util import get_logger

logger = get_logger(__name__)


class BaseEmbeddingService(EmbeddingInterface):
    """
    Base class that implements common functionality for embedding services.

    This class provides default implementations for methods that can be
    derived from other methods, reducing code duplication in concrete implementations.
    """

    def __init__(self, model_name: str, batch_size: int = 32):
        """
        Initialize the base embedding service.

        Args:
            model_name: Name/identifier of the embedding model
            batch_size: Maximum number of texts to process in a single batch
        """
        self.model_name = model_name
        self.batch_size = batch_size
        logger.info(f"Initialized embedding service with model: {model_name}")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a text string.

        Default implementation that calls get_embedding.
        Concrete classes should override this if they have a more efficient implementation.

        Args:
            text: The text string to be embedded

        Returns:
            Embedding vector as a list of floats
        """
        return await self.get_embedding(text)

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text input.

        Default implementation that calls get_embeddings.
        Concrete classes should override this if they have a more efficient implementation.

        Args:
            text: The input text to embed

        Returns:
            Embedding vector as a list of floats
        """
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else []

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents.

        Default implementation that processes documents in batches.

        Args:
            documents: A list of Document objects to be embedded

        Returns:
            The list of Document objects with their embedding attributes populated
        """
        if not documents:
            return []

        # Process documents in batches
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            texts = [doc.content for doc in batch]

            # Generate embeddings
            embeddings = await self.get_embeddings(texts)

            # Assign embeddings to documents
            for j, doc in enumerate(batch):
                doc.embedding = embeddings[j]

        return documents

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text inputs.

        This method must be implemented by concrete classes.
        The base implementation raises NotImplementedError.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors for the input texts

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement get_embeddings")

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a query string.

        Default implementation that calls get_embedding.
        Concrete classes can override this if query embedding differs from regular text embedding.

        Args:
            query: The query string to be embedded

        Returns:
            Embedding vector as a list of floats
        """
        return await self.get_embedding(query)