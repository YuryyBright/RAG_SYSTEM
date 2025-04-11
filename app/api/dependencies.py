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
from app.config import settings

# Core Interfaces
from core.interfaces.document_store import DocumentStoreInterface
from core.interfaces.embedding import EmbeddingInterface
from core.interfaces.indexing import IndexInterface
from core.interfaces.llm import LLMInterface
from core.interfaces.reranking import RerankerInterface
from core.interfaces.theme_repository import ThemeRepositoryInterface
from core.use_cases.file_processing import FileProcessingUseCase

# Use Cases
from core.use_cases.query import QueryProcessor
from core.use_cases.theme import ThemeUseCase

# Adapters
from adapters.storage.document_store import DocumentStore
from adapters.indexing.faiss_hnsw import FaissHNSWIndex
from adapters.reranking.cross_encoder import CrossEncoderReranker
from adapters.llm.mistral import MistralLLM

# Uncomment if using OpenAI instead of Instructor
# from adapters.embedding.open_ai import OpenAIEmbedding

# Infrastructure
from infrastructure.database.repository.theme_repository import ThemeRepository
from infrastructure.database.repository.document_repository import DocumentRepository

from infrastructure.database.repository import get_async_db




# === Infrastructure ===

def get_document_repository(db: AsyncSession = Depends(get_async_db)) -> DocumentRepository:
    """Provides DocumentRepository bound to a DB session."""
    return DocumentRepository(db)


def get_theme_repository(db: AsyncSession = Depends(get_async_db)) -> ThemeRepository:
    """Provides ThemeRepository bound to a DB session."""
    return ThemeRepository(db)


# === Embedding / Model Services ===

def get_embedding_service() -> EmbeddingInterface:
    """Provides the embedding service as configured."""
    if settings.EMBEDDING_SERVICE == "instructor":
        return InstructorEmbedding(model_name=settings.INSTRUCTOR_MODEL_NAME)
    # elif settings.EMBEDDING_SERVICE == "openai":
    #     return OpenAIEmbedding(api_key=settings.OPENAI_API_KEY)
    else:
        raise ValueError(f"Unsupported embedding service: {settings.EMBEDDING_SERVICE}")


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



