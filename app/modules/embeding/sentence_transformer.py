# app/modules/embedding/sentence_transformer.py
from typing import List
from sentence_transformers import SentenceTransformer

from application.services.base_embedding_service import BaseEmbeddingService
from utils.logger_util import get_logger

logger = get_logger(__name__)


class SentenceTransformerEmbedding(BaseEmbeddingService):
    """
    Implementation of SentenceTransformer-based embeddings.

    This class uses Sentence Transformers to generate embeddings for
    documents and queries.
    """

    def __init__(
            self,
            model_name: str = "all-MiniLM-L6-v2",
            batch_size: int = 8
    ):
        """
        Initialize the SentenceTransformer embedding service.

        Args:
            model_name: Name of the model from Hugging Face
            batch_size: Batch size for processing
        """
        super().__init__(model_name=model_name, batch_size=batch_size)
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info(f"SentenceTransformer model loaded successfully")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text inputs.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors for the input texts
        """
        if not texts:
            return []

        try:
            # Process in batches
            results = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]

                # Generate embeddings
                batch_embeddings = self.model.encode(batch)

                # Convert numpy arrays to lists
                batch_embeddings = [emb.tolist() for emb in batch_embeddings]
                results.extend(batch_embeddings)

            return results

        except Exception as e:
            logger.error(f"Error generating SentenceTransformer embeddings: {str(e)}")
            raise

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a text string.

        Implementation optimized for single text input.

        Args:
            text: The text string to be embedded

        Returns:
            List of floats representing the embedding of the text
        """
        embedding = self.model.encode(text)
        return embedding.tolist()