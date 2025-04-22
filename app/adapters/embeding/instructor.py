# app/adapters/embedding/instructor.py
from typing import List
import os

from sentence_transformers import SentenceTransformer

from core.entities.document import Document
from core.interfaces.base_embedding_service import BaseEmbeddingService
from utils.logger_util import get_logger

logger = get_logger(__name__)


class InstructorEmbedding(BaseEmbeddingService):
    """
    Implementation of INSTRUCTOR embedding model.

    This class uses the INSTRUCTOR embedding model to generate embeddings for
    documents and queries. It provides instruction-based embeddings that can be
    customized for different tasks.
    """

    def __init__(
            self,
            model_name: str = "models/instructors/instructor-xl",
            instruction: str = "Represent the document for retrieval:",
            query_instruction: str = "Represent the question for retrieving relevant documents:",
            batch_size: int = 8,
            device: str = "cpu"
    ):
        """
        Initialize the INSTRUCTOR embedding service.

        Args:
            model_name: The name/path of the INSTRUCTOR embedding model to use
            instruction: The instruction to guide document embedding generation
            query_instruction: The instruction to guide query embedding generation
            batch_size: The maximum number of documents to process in a single batch
            device: The device to run the model on ('cpu' or 'cuda')
        """
        super().__init__(model_name=model_name, batch_size=batch_size)
        self.model_name = model_name.replace("\\", "/")
        self.instruction = instruction
        self.query_instruction = query_instruction
        self.device = device

        if not os.path.exists(self.model_name):
            raise FileNotFoundError(f"Model not found at path: {self.model_name}")

        logger.info(f"✅ Loading model from local path: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        # Manually move model if needed
        if self.device:
            logger.info(f"⚙️ Moving model to device: {self.device}")
            self.model = self.model.to(self.device)

        self.model.set_pooling_include_prompt(False)
        logger.info(f"✅ INSTRUCTOR model initialized successfully")

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

        results = []
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            try:
                # Create instruction pairs for each text in the batch
                instruction_pairs = [[self.instruction, text] for text in batch]

                # Generate embeddings
                batch_embeddings = self.model.encode(instruction_pairs)

                # Convert numpy arrays to lists
                batch_embeddings = [emb.tolist() for emb in batch_embeddings]
                results.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Error generating INSTRUCTOR embeddings: {str(e)}")
                raise

        return results

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a query string using the INSTRUCTOR model.

        Args:
            query: The query string to be embedded

        Returns:
            List of floats representing the embedding of the query
        """
        # Create instruction pair for the query
        instruction_pair = [[self.query_instruction, query]]

        try:
            # Generate embedding
            embedding = self.model.encode(instruction_pair)
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a text string using the INSTRUCTOR model.

        Args:
            text: The text string to be embedded

        Returns:
            List of floats representing the embedding of the text
        """
        # Create instruction pair for the text
        instruction_pair = [[self.instruction, text]]

        try:
            # Generate embedding
            embedding = self.model.encode(instruction_pair)
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error generating text embedding: {str(e)}")
            raise