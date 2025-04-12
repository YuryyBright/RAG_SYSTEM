# app/adapters/embedding/cached_embedding.py
from typing import List, Optional
import hashlib
from app.core.entities.document import Document
from app.core.interfaces.embedding import EmbeddingInterface
from app.infrastructure.cache.redis_cache import RedisCache


class CachedEmbeddingService(EmbeddingInterface):
    """
    Cache wrapper for embedding services to improve performance.

    This class caches embeddings in Redis to avoid recomputing embeddings
    for the same content.
    """

    def __init__(
            self,
            embedding_service: EmbeddingInterface,
            cache_service: RedisCache,
            ttl: int = 3600
    ):
        """
        Initialize with underlying embedding service and cache.

        Args:
            embedding_service: The actual embedding service to wrap
            cache_service: Redis cache for storing embeddings
            ttl: Time-to-live for cached embeddings in seconds
        """
        self.embedding_service = embedding_service
        self.cache_service = cache_service
        self.ttl = ttl

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """Generate embeddings for documents, using cache when available."""
        docs_to_embed = []

        # Check cache for each document
        for doc in documents:
            cache_key = f"embedding:{doc.id}"
            cached_embedding = await self.cache_service.get(cache_key)

            if cached_embedding:
                doc.embedding = cached_embedding
            else:
                docs_to_embed.append(doc)

        # Embed documents not found in cache
        if docs_to_embed:
            await self.embedding_service.embed_documents(docs_to_embed)

            # Store new embeddings in cache
            for doc in docs_to_embed:
                cache_key = f"embedding:{doc.id}"
                await self.cache_service.set(cache_key, doc.embedding, ttl=self.ttl)

        return documents

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query, using cache when available."""
        # Create a cache key based on query content
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"query_embedding:{query_hash}"

        # Check cache
        cached_embedding = await self.cache_service.get(cache_key)
        if cached_embedding:
            return cached_embedding

        # Generate new embedding if not in cache
        embedding = await self.embedding_service.embed_query(query)

        # Store in cache
        await self.cache_service.set(cache_key, embedding, ttl=self.ttl)

        return embedding