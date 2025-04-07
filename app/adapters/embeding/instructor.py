# app/adapters/embedding/instructor.py
from typing import List
import os
from InstructorEmbedding import INSTRUCTOR
from core.entities.document import Document
from core.interfaces.embedding import EmbeddingInterface


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
            model_name: str = "hkunlp/instructor-large",
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
        self.model_name = model_name
        self.instruction = instruction
        self.query_instruction = query_instruction
        self.batch_size = batch_size
        self.device = device

        # Load the model
        self.model = INSTRUCTOR(model_name, device=device)

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents using the INSTRUCTOR model.

        Args:
            documents (List[Document]): A list of Document objects to be embedded.

        Returns:
            List[Document]: The list of Document objects with their embedding attributes populated.
        """
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