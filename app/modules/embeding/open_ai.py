# app/modules/embedding/onnx.py
import os
from typing import List
import openai

from application.services.base_embedding_service import BaseEmbeddingService
from utils.logger_util import get_logger

logger = get_logger(__name__)


class OpenAIEmbedding(BaseEmbeddingService):
    """
    OpenAI embedding implementation.

    This class uses OpenAI's embedding API to generate embeddings for documents and queries.
    """

    def __init__(
            self,
            model_name: str = "text-embedding-ada-002",
            api_key: str = None,
            batch_size: int = 5
    ):
        """
        Initialize the OpenAI embedding service.

        Args:
            model_name: The name of the OpenAI embedding model to use
            api_key: The OpenAI API key. If None, it will be read from the environment
            batch_size: The maximum number of documents to process in a single API call
        """
        super().__init__(model_name=model_name, batch_size=batch_size)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set it in the environment as OPENAI_API_KEY or pass it directly.")

        # Set the API key for the openai package
        openai.api_key = self.api_key
        logger.info(f"Initialized OpenAI embedding with model: {model_name}")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using OpenAI's API.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (as lists of floats)
        """
        if not texts:
            return []

        results = []
        # Process in batches to avoid API limits
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            try:
                # Call the OpenAI API
                response = await openai.Embedding.acreate(
                    model=self.model_name,
                    input=batch
                )

                # Extract embeddings
                batch_embeddings = [item["embedding"] for item in response["data"]]
                results.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Error generating OpenAI embeddings: {str(e)}")
                raise

        return results

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a text string using OpenAI's API.

        Implementation optimized for single text input.

        Args:
            text: The text string to be embedded

        Returns:
            List of floats representing the embedding of the text
        """
        response = await openai.Embedding.acreate(
            model=self.model_name,
            input=text
        )

        return response["data"][0]["embedding"]