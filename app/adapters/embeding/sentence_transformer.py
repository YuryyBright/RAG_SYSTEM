# app/adapters/embedding/sentence_transformer.py
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.entities.document import Document
from app.core.interfaces.embedding import EmbeddingInterface


class SentenceTransformerEmbedding(EmbeddingInterface):
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
            model_name (str): Name of the model from Hugging Face
            batch_size (int): Batch size for processing
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name)

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """Generate embeddings for a list of documents."""
        # Process documents in batches
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            texts = [doc.content for doc in batch]

            # Generate embeddings
            embeddings = self.model.encode(texts)

            # Assign embeddings to documents
            for j, doc in enumerate(batch):
                doc.embedding = embeddings[j].tolist()

        return documents

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query string."""
        embedding = self.model.encode(query)
        return embedding.tolist()