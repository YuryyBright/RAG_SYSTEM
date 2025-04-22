# core/interfaces/embedding.py
from abc import ABC, abstractmethod
from typing import List
from domain.entities.document import Document


class EmbeddingInterface(ABC):
    """Interface for embedding services."""

    @abstractmethod
    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        pass

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass