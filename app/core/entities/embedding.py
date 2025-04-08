# core/services/huggingface_embedding.py

from typing import List
from core.entities.document import Document
from core.interfaces.embedding import EmbeddingInterface
from sentence_transformers import SentenceTransformer
import asyncio

class HuggingFaceEmbeddingService(EmbeddingInterface):
    """
    Concrete implementation of EmbeddingInterface using HuggingFace SentenceTransformer.

    This service generates vector embeddings for documents and queries.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.

        Args:
            model_name (str): Name of the HuggingFace SentenceTransformer model.
        """
        self.model = SentenceTransformer(model_name)

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Generate embeddings for a list of documents.

        Args:
            documents (List[Document]): List of Document objects.

        Returns:
            List[Document]: Documents with populated `embedding` attribute.
        """
        contents = [doc.content for doc in documents]
        embeddings = await asyncio.to_thread(self.model.encode, contents, show_progress_bar=False)

        for doc, emb in zip(documents, embeddings):
            doc.embedding = emb.tolist()

        return documents

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a single query string.

        Args:
            query (str): The query string.

        Returns:
            List[float]: Embedding vector.
        """
        embedding = await asyncio.to_thread(self.model.encode, query)
        return embedding.tolist()
