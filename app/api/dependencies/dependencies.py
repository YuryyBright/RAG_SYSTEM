"""
Dependency Injection Providers for FastAPI.

This module configures the DI system for:
- Repositories (Document, Theme)
- Services (Embedding, Indexing, Reranking, LLM)
- Use Cases (Theme, QueryProcessor)
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.embeding.embedding_factory import get_embedding_service
from adapters.embeding.instructor import InstructorEmbedding
from adapters.embeding.open_ai import OpenAIEmbedding
from adapters.embeding.sentence_transformer import SentenceTransformerEmbedding
from adapters.indexing.chroma_index import ChromaVectorIndex
from adapters.indexing.milvus import MilvusVectorIndex
from adapters.storage.file_manager import FileManager

# Fix typo in import path

from app.config import settings

# Core Interfaces
from app.core.interfaces.document_store import DocumentStoreInterface
from app.core.interfaces.embedding import EmbeddingInterface
from app.core.interfaces.indexing import IndexInterface
from app.core.interfaces.llm import LLMInterface
from app.core.interfaces.reranking import RerankerInterface
from app.core.interfaces.theme_repository import ThemeRepositoryInterface
from app.core.use_cases.file_processing import FileProcessingUseCase, FileProcessor

# Use Cases
from app.core.use_cases.query import QueryProcessor
from app.core.use_cases.theme import ThemeUseCase

# Adapters
from app.adapters.storage.document_store import DocumentStore
from app.adapters.indexing.faiss_hnsw import FaissVectorIndex
from app.adapters.reranking.cross_encoder import CrossEncoderReranker
from app.adapters.llm.mistral import MistralLLM

# Infrastructure
from app.infrastructure.database.repository.theme_repository import ThemeRepository
from app.infrastructure.database.repository.document_repository import DocumentRepository

from app.infrastructure.database.repository import get_async_db
from app.utils.logger_util import get_logger
from core.services.auth_service import AuthService
from core.services.chunking_service import ChunkingService


from core.services.task_services import TaskManager
from core.services.vector_index_services import VectorIndexService
from infrastructure.database.repository.file_repository import FileRepository
from infrastructure.database.repository.task_repository import TaskRepository
from api.websockets.task_updates import get_task_update_manager, TaskUpdateManager
from utils.validators import validate_embedding_dimensions

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


def get_task_manager(db: AsyncSession = Depends(get_async_db)) -> TaskManager:
    """Helper to provide a TaskManager with a DB session."""
    return TaskManager(db)


def get_auth_service(db: AsyncSession = Depends(get_async_db)) -> AuthService:
    """
    A FastAPI dependency that returns an AuthService with a real AsyncSession.
    """
    return AuthService(db)


def get_theme_repository(db: AsyncSession = Depends(get_async_db)) -> ThemeRepository:
    """Provides ThemeRepository bound to a DB session."""
    return ThemeRepository(db)


def get_file_manager() -> FileManager:
    """Return a new FileManager instance."""
    return FileManager()
# === Embedding / Model Services ===





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


# === Use Cases ===

def get_theme_use_case_p(
        theme_repository: ThemeRepository = Depends(get_theme_repository),
        # document_store: DocumentStore = Depends(get_document_store),
        # file_manager: FileManager = Depends(get_file_manager)
) -> ThemeUseCase:
    """Provides the ThemeUseCase with repository + store dependencies."""
    return ThemeUseCase(
        theme_repository=theme_repository,
        document_store=None,
        file_manager=None
    )


def get_files_store(db: AsyncSession = Depends(get_async_db))-> FileRepository:
    return FileRepository(db)

def get_theme_use_case(
        theme_repository: ThemeRepository = Depends(get_theme_repository),
        document_store: DocumentStore = Depends(get_document_store),
        file_manager: FileManager = Depends(get_file_manager)
) -> ThemeUseCase:
    """Provides the ThemeUseCase with repository + store dependencies."""
    return ThemeUseCase(
        theme_repository=theme_repository,
        document_store=document_store,
        file_manager=file_manager
    )





async def get_chunking_service() -> ChunkingService:
    """
    Get chunking service instance.
    """
    # In a real implementation, you might need to pass configuration here
    return ChunkingService()


async def get_vector_index(
        db: Annotated[AsyncSession, Depends(get_async_db)]
) -> IndexInterface:
    """
    Provide an initialized vector index implementation based on application settings.

    This dependency function:
      • Reads the VECTOR_DB_TYPE from your settings (faiss, chroma, milvus).
      • Creates and returns the corresponding vector index instance.
      • Injects an async DB session if needed (e.g. for Milvus).

    Returns
    -------
    IndexInterface
        The vector index adapter for storing and querying document embeddings.
    """
    vector_db_type = settings.VECTOR_DB_TYPE.lower()

    if vector_db_type == "chroma":
        return ChromaVectorIndex(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            persistence_path=settings.CHROMA_DB_PATH,
            embedding_dimension=settings.EMBEDDING_DIMENSION,
        )
    elif vector_db_type == "faiss":
        return FaissVectorIndex(dimension=settings.EMBEDDING_DIMENSION)
    elif vector_db_type == "milvus":
        return MilvusVectorIndex(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            dimension=settings.EMBEDDING_DIMENSION,
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
    else:
        # Fallback to FAISS
        return FaissVectorIndex(dimension=settings.EMBEDDING_DIMENSION)


def get_query_processor(
        embedding_service: EmbeddingInterface = Depends(get_embedding_service),
        index_service: IndexInterface = Depends(get_vector_index),
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



def get_file_processor(db: AsyncSession = Depends(get_async_db)) -> FileProcessor:
    file_repo = FileRepository(db)
    return FileProcessor(file_repository=file_repo)

async def file_processing_use_case(
        file_processor: FileProcessor = Depends(get_file_processor),
        chunking_service: ChunkingService = Depends(get_chunking_service),
        embedding_service: EmbeddingInterface = Depends(get_embedding_service),
        document_store: DocumentStore = Depends(get_document_store),
        vector_index: VectorIndexService = Depends(get_vector_index),
        task_update_manager: TaskUpdateManager = Depends(get_task_update_manager)

) -> FileProcessingUseCase:
    """
    Provides a FileProcessingUseCase instance via FastAPI's dependency injection.

    This function injects all the required components:
      - file_processor: Responsible for file reading/parsing
      - embedding_service: For generating vector embeddings
      - document_store: For persisting documents
      - vector_index: For storing/retrieving vectors
      - file_manager: For file storage / management tasks
      - chunking_service:  For file CHUNKING / management tasks

    Returns
    -------
    FileProcessingUseCase
        A configured instance capable of processing and indexing files in the RAG pipeline.
    """
    return FileProcessingUseCase(
        file_processor=file_processor,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        document_store=document_store,
        vector_index=vector_index,
        task_update_manager = task_update_manager,
    )
