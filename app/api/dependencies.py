"""
Dependency Injection Providers for FastAPI.

This module configures the DI system for:
- Repositories (Document, Theme)
- Services (Embedding, Indexing, Reranking, LLM)
- Use Cases (Theme, QueryProcessor)
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.embeding.instructor import InstructorEmbedding
from adapters.embeding.open_ai import OpenAIEmbedding

# Fix typo in import path

from app.config import settings

# Core Interfaces
from app.core.interfaces.document_store import DocumentStoreInterface
from app.core.interfaces.embedding import EmbeddingInterface
from app.core.interfaces.indexing import IndexInterface
from app.core.interfaces.llm import LLMInterface
from app.core.interfaces.reranking import RerankerInterface
from app.core.interfaces.theme_repository import ThemeRepositoryInterface
from app.core.use_cases.file_processing import FileProcessingUseCase

# Use Cases
from app.core.use_cases.query import QueryProcessor
from app.core.use_cases.theme import ThemeUseCase

# Adapters
from app.adapters.storage.document_store import DocumentStore
from app.adapters.indexing.faiss_hnsw import FaissHNSWIndex
from app.adapters.reranking.cross_encoder import CrossEncoderReranker
from app.adapters.llm.mistral import MistralLLM

# Infrastructure
from app.infrastructure.database.repository.theme_repository import ThemeRepository
from app.infrastructure.database.repository.document_repository import DocumentRepository

from app.infrastructure.database.repository import get_async_db
from app.utils.logger_util import get_logger


logger = get_logger(__name__)

# === Infrastructure ===
# async def get_cache_service() -> RedisCache:
#     """
#     Provides the Redis cache service.
#
#     This dependency is used to inject the cache service into other
#     services that need caching functionality.
#
#     Returns:
#         RedisCache: The configured Redis cache service
#     """
#     return await get_redis_cache()


def get_document_repository(db: AsyncSession = Depends(get_async_db)) -> DocumentRepository:
    """Provides DocumentRepository bound to a DB session."""
    return DocumentRepository(db)


def get_theme_repository(db: AsyncSession = Depends(get_async_db)) -> ThemeRepository:
    """Provides ThemeRepository bound to a DB session."""
    return ThemeRepository(db)


# === Embedding / Model Services ===

def get_embedding_service(cache_service=None) -> EmbeddingInterface:
    """
    Factory function that provides the configured embedding service.

    This creates and configures the appropriate embedding model implementation
    based on application settings. The embedding service is used to convert
    documents and queries into vector representations for semantic search.

    Args:
        cache_service: Optional cache service to store/retrieve embeddings

    Returns:
        EmbeddingInterface: The configured embedding service implementation

    Raises:
        ValueError: If the configured embedding service is not supported
    """
    embedding_service = settings.EMBEDDING_SERVICE.lower()
    logger.debug(f"Initializing embedding service: {embedding_service}")

    if embedding_service == "instructor":
        return InstructorEmbedding(
            model_name=settings.INSTRUCTOR_MODEL_NAME,
            instruction=settings.EMBEDDING_INSTRUCTION,
            query_instruction=settings.QUERY_INSTRUCTION,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            device=settings.EMBEDDING_DEVICE
        )
    elif embedding_service == "openai":
        return OpenAIEmbedding(
            model_name=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
            batch_size=settings.OPENAI_BATCH_SIZE
        )
    elif embedding_service == "sentence_transformer":
        # You could add support for sentence-transformers models
        from adapters.embeding.sentence_transformer import SentenceTransformerEmbedding
        return SentenceTransformerEmbedding(
            model_name=settings.SENTENCE_TRANSFORMER_MODEL_NAME,
            batch_size=settings.EMBEDDING_BATCH_SIZE
        )
    else:
        available_services = ["instructor", "openai", "sentence_transformer"]
        logger.error(f"Unsupported embedding service: {embedding_service}")
        raise ValueError(
            f"Unsupported embedding service: {embedding_service}. "
            f"Available options: {', '.join(available_services)}"
        )


def get_indexing_service(
    document_repository: DocumentRepository = Depends(get_document_repository)
) -> IndexInterface:
    """Provides FAISS-based vector indexing service."""
    return FaissHNSWIndex(
        document_repository=document_repository,
        dimension=settings.EMBEDDING_DIMENSION
    )


def get_llm_service() -> LLMInterface:
    """Provides Mistral or other LLM."""
    return MistralLLM(model_name=settings.LLM_MODEL)


def get_reranker_service() -> RerankerInterface:
    """Provides reranker model interface."""
    return CrossEncoderReranker(model_name=settings.RERANKER_MODEL)


# === Storage Services ===

def get_document_store(
    document_repository: DocumentRepository = Depends(get_document_repository),
    embedding_service: EmbeddingInterface = Depends(get_embedding_service)
) -> DocumentStoreInterface:
    """Provides a DocumentStore instance."""
    return DocumentStore(
        document_repository=document_repository,
        embedding_service=embedding_service,
        storage_path=settings.DOCUMENT_STORAGE_PATH
    )

# Dependency to get the file processing use case
def file_processing_use_case():
    return FileProcessingUseCase()

# === Use Cases ===

def get_theme_use_case(
    theme_repository: ThemeRepositoryInterface = Depends(get_theme_repository),
    document_store: DocumentStoreInterface = Depends(get_document_store)
) -> ThemeUseCase:
    """Provides the ThemeUseCase with repository + store dependencies."""
    return ThemeUseCase(
        theme_repository=theme_repository,
        document_store=document_store
    )


def get_query_processor(
    embedding_service: EmbeddingInterface = Depends(get_embedding_service),
    index_service: IndexInterface = Depends(get_indexing_service),
    reranker_service: RerankerInterface = Depends(get_reranker_service),
    llm_service: LLMInterface = Depends(get_llm_service)
) -> QueryProcessor:
    """Provides a QueryProcessor instance with all AI services."""
    return QueryProcessor(
        embedding_service=embedding_service,
        index_service=index_service,
        reranker_service=reranker_service,
        llm_service=llm_service,
        score_threshold=settings.SCORE_THRESHOLD
    )