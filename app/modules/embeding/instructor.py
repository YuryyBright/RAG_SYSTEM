# app/modules/embedding/instructor.py
from typing import List
import os
import torch
from sentence_transformers import SentenceTransformer

from application.services.base_embedding_service import BaseEmbeddingService
from config import settings
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
            model_name: str = "hkunlp/instructor-xl",
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

        # Get the base directory for models from environment variable or use default
        base_models_dir = settings.INSTRUCTOR_BASE_DIR

        # Check if the model_name is a Hugging Face model ID or a local path
        if "/" in model_name and not os.path.exists(model_name):
            # Construct path to local model directory
            local_model_path = os.path.join(base_models_dir, model_name.split("/")[-1])

            if os.path.exists(local_model_path):
                self.model_name = local_model_path
                logger.info(f"Found model in local directory: {self.model_name}")
            else:
                # If not found locally, try to use the original model name
                # (which might be downloaded from Hugging Face)
                self.model_name = model_name
                logger.warning(f"Model not found locally, attempting to use: {self.model_name}")
        else:
            self.model_name = model_name

        self.model_name = self.model_name.replace("\\", "/")
        self.instruction = instruction
        self.query_instruction = query_instruction
        self.device = device

        try:
            logger.info(f"Loading model from: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)

            # Manually move model if needed
            if self.device:
                logger.info(f"⚙️ Moving model to device: {self.device}")
                self.model = self.model.to(self.device)
            else:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.set_pooling_include_prompt(False)
            logger.info(f"✅ INSTRUCTOR model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to load model from {self.model_name}: {str(e)}")
            raise FileNotFoundError(f"Model not found at path: {self.model_name}")

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