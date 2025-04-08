# app/adapters/embedding/open_ai.py
import os
from typing import List
import openai
from core.entities.document import Document
from core.interfaces.embedding import EmbeddingInterface


class OpenAIEmbedding(EmbeddingInterface):
    """
    OpenAI embedding implementation.

    This class uses OpenAI's embedding API to generate embeddings for documents and queries.

    Attributes:
        model_name (str): The name of the OpenAI embedding model to use.
        api_key (str): The OpenAI API key for authentication.
        batch_size (int): The maximum number of documents to process in a single API call.
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
            model_name (str): The name of the OpenAI embedding model to use.
            api_key (str): The OpenAI API key. If None, it will be read from the environment.
            batch_size (int): The maximum number of documents to process in a single API call.
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.batch_size = batch_size

        # Set the API key for the openai package
        openai.api_key = self.api_key

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents using OpenAI's API.

        Args:
            documents (List[Document]): A list of Document objects to be embedded.

        Returns:
            List[Document]: The list of Document objects with their embedding attributes populated.
        """
        # Process documents in batches
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            texts = [doc.content for doc in batch]

            # Call the OpenAI API
            response = await openai.Embedding.acreate(
                model=self.model_name,
                input=texts
            )

            # Extract embeddings and assign them to documents
            for j, doc in enumerate(batch):
                doc.embedding = response["data"][j]["embedding"]

        return documents

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a query string using OpenAI's API.

        Args:
            query (str): The query string to be embedded.

        Returns:
            List[float]: A list of floats representing the embedding of the query.
        """
        response = await openai.Embedding.acreate(
            model=self.model_name,
            input=query
        )

        return response["data"][0]["embedding"]