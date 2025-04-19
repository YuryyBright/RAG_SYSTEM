# app/core/services/embedding_service.py
from typing import List, Dict, Any
import logging
from abc import ABC, abstractmethod
import numpy as np

from core.entities.document import Document
from core.interfaces.embedding import EmbeddingInterface
from utils.logger_util import get_logger

logger = get_logger(__name__)

class EmbeddingService(EmbeddingInterface):
    """Service for generating embeddings from text."""

    def __init__(self, model_name: str = "default", dimensions: int = 1536):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the embedding model to use
            dimensions: Dimensionality of the embedding model
        """
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = 32  # Default batch size
        logger.info(f"Initialized EmbeddingService with model {model_name} ({dimensions} dimensions)")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (as lists of floats)
        """
        if not texts:
            return []

        results = []
        # Process in batches to avoid overloading the API or memory
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self._embed_batch(batch)
            results.extend(batch_embeddings)

        return results

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as a list of floats
        """
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else []

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts using the selected embedding model.

        In a real implementation, this would call an actual embedding model API.
        For now, we'll generate random embeddings for demonstration.

        Args:
            texts: Batch of text strings to embed

        Returns:
            List of embedding vectors
        """
        try:
            # In a real implementation, you would call your embedding model here
            # For demonstration, we'll generate random vectors of the correct dimension
            embeddings = []
            for text in texts:
                # Generate a deterministic but "random" embedding based on text content
                # to ensure consistent results for the same input
                np.random.seed(hash(text) % 2 ** 32)
                embedding = np.random.randn(self.dimensions).tolist()
                embeddings.append(embedding)

            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    def get_dimensions(self) -> int:
        """
        Get the dimensionality of the embeddings.

        Returns:
            Number of dimensions in the embedding vectors
        """
        return self.dimensions

    def set_batch_size(self, batch_size: int) -> None:
        """
        Set the batch size for embedding generation.

        Args:
            batch_size: Number of texts to process in a single batch
        """
        if batch_size < 1:
            raise ValueError("Batch size must be at least 1")
        self.batch_size = batch_size
        logger.debug(f"Embedding batch size set to {batch_size}")

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents.

        Args:
            documents (List[Document]): A list of Document objects to embed.

        Returns:
            List[Document]: The same list with updated embedding fields.
        """
        if not documents:
            return []

        texts = [doc.content for doc in documents]
        embeddings = await self.get_embeddings(texts)

        for doc, embedding in zip(documents, embeddings):
            doc.embedding = embedding

        return documents

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a query string.

        Args:
            query (str): The query string to be embedded.

        Returns:
            List[float]: Embedding vector for the query.
        """
        return await self.get_embedding(query)