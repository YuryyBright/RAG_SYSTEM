# app/adapters/embedding/instructor.py
from typing import List
import os
from InstructorEmbedding import INSTRUCTOR
from sentence_transformers import SentenceTransformer

from core.entities.document import Document
from core.interfaces.embedding import EmbeddingInterface
from utils.logger_util import get_logger

logger = get_logger(__name__)


class InstructorEmbedding(EmbeddingInterface):
    """
    Implementation of INSTRUCTOR embedding model.

    This class uses the INSTRUCTOR embedding model to generate embeddings for
    documents and queries. It provides instruction-based embeddings that can be
    customized for different tasks.

    Attributes:
        model_name (str): The name/path of the INSTRUCTOR embedding model to use.
        instruction (str): The instruction to guide the embedding generation.
        batch_size (int): The maximum number of documents to process in a single batch.
        device (str): The device to run the model on ('cpu' or 'cuda').
    """

    def __init__(
            self,
            model_name: str = "models/instructor-large",
            instruction: str = "Represent the document for retrieval:",
            query_instruction: str = "Represent the question for retrieving relevant documents:",
            batch_size: int = 8,
            device: str = "cpu"
    ):
        """
        Initialize the INSTRUCTOR embedding service.

        Args:
            model_name (str): The name/path of the INSTRUCTOR embedding model to use.
            instruction (str): The instruction to guide document embedding generation.
            query_instruction (str): The instruction to guide query embedding generation.
            batch_size (int): The maximum number of documents to process in a single batch.
            device (str): The device to run the model on ('cpu' or 'cuda').
        """
        self.model_name = model_name.replace("\\", "/")
        self.instruction = instruction
        self.query_instruction = query_instruction
        self.batch_size = batch_size
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

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents using the INSTRUCTOR model.

        Args:
            documents (List[Document]): A list of Document objects to be embedded.

        Returns:
            List[Document]: The list of Document objects with their embedding attributes populated.
        """
        if not documents:
            return []

        # Process documents in batches
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            texts = [doc.content for doc in batch]

            # Create instruction pairs
            instruction_pairs = [[self.instruction, text] for text in texts]

            # Generate embeddings
            embeddings = self.model.encode(instruction_pairs)

            # Assign embeddings to documents
            for j, doc in enumerate(batch):
                doc.embedding = embeddings[j].tolist()

        return documents

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a query string using the INSTRUCTOR model.

        Args:
            query (str): The query string to be embedded.

        Returns:
            List[float]: A list of floats representing the embedding of the query.
        """
        # Create instruction pair for the query
        instruction_pair = [[self.query_instruction, query]]

        # Generate embedding
        embedding = self.model.encode(instruction_pair)

        return embedding[0].tolist()

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a text string using the INSTRUCTOR model.

        Args:
            text (str): The text string to be embedded.

        Returns:
            List[float]: A list of floats representing the embedding of the text.
        """
        # Create instruction pair for the text
        instruction_pair = [[self.instruction, text]]

        # Generate embedding
        embedding = self.model.encode(instruction_pair)

        return embedding[0].tolist()

    async def get_embedding(self, text: str) -> List[float]:
        """
        Get a single embedding using the embed_text logic.
        Alias method for interface compatibility.

        Args:
            text (str): The text to embed.

        Returns:
            List[float]: The generated embedding.
        """
        return await self.embed_text(text)

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text inputs.

        Args:
            texts (List[str]): List of text strings to embed.

        Returns:
            List[List[float]]: List of embedding vectors for the input texts.
        """
        if not texts:
            return []

        results = []
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            # Create instruction pairs for each text in the batch
            instruction_pairs = [[self.instruction, text] for text in batch]

            # Generate embeddings
            batch_embeddings = self.model.encode(instruction_pairs)

            # Convert numpy arrays to lists
            batch_embeddings = [emb.tolist() for emb in batch_embeddings]
            results.extend(batch_embeddings)

        return results