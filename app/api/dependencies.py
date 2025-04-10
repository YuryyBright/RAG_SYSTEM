"""
This module defines dependency injection functions for various services used in the application.

Dependencies:
- DocumentRepository: Repository for document DB operations.
- DocumentLoader: Singleton instance for loading documents.
- EmbeddingService: Provides embedding functionality using the specified model.
- IndexingService: Provides indexing functionality using the specified document store and embedding dimension.
- LLMService: Provides large language model functionality using the specified model.
- RerankerService: Provides reranking functionality using the specified model.
- QueryProcessor: Processes queries using the provided embedding, indexing, reranking, and LLM services.

Functions:
- get_db_session: Returns a database session for use with repositories.
- get_document_repository: Returns a DocumentRepository instance with a DB session.
- get_document_loader: Returns the singleton DocumentLoader instance.
- get_embedding_service: Returns an instance of the embedding service.
- get_indexing_service: Returns an instance of the indexing service.
- get_llm_service: Returns an instance of the LLM service.
- get_reranker_service: Returns an instance of the reranking service.
- get_query_processor: Returns an instance of the QueryProcessor with all required services.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.mistral import MistralLLM
from core.interfaces.embedding import EmbeddingInterface
from core.interfaces.indexing import IndexInterface
from core.interfaces.llm import LLMInterface
from core.interfaces.reranking import RerankerInterface

from app.adapters.indexing.faiss_hnsw import FaissHNSWIndex
from app.adapters.embeding.instructor import InstructorEmbedding
from app.adapters.reranking.cross_encoder import CrossEncoderReranker
from app.infrastructure.database.repository.document_repository import DocumentRepository
from app.infrastructure.loaders.document_loader import DocumentLoader
from app.config import settings
from core.use_cases.query import QueryProcessor
from infrastructure.database.repository import get_async_db

# Singleton instances
document_loader = DocumentLoader()

def get_document_loader() -> DocumentLoader:
    """Returns the singleton DocumentLoader instance."""
    return document_loader

def get_document_repository(db: AsyncSession = Depends(get_async_db)) -> DocumentRepository:
    """Returns a DocumentRepository instance with a database session."""
    return DocumentRepository(db)

def get_embedding_service() -> EmbeddingInterface:
    """Returns an instance of the embedding service."""
    return InstructorEmbedding(model_name=settings.EMBEDDING_MODEL)

def get_indexing_service(
    document_repository: DocumentRepository = Depends(get_document_repository)
) -> IndexInterface:
    """Returns an instance of the indexing service."""
    return FaissHNSWIndex(
        document_repository=document_repository,
        dimension=settings.EMBEDDING_DIMENSION
    )

def get_llm_service() -> LLMInterface:
    """Returns an instance of the LLM service."""
    return MistralLLM(model_name=settings.LLM_MODEL)

def get_reranker_service() -> RerankerInterface:
    """Returns an instance of the reranking service."""
    return CrossEncoderReranker(model_name=settings.RERANKER_MODEL)

def get_query_processor(
    embedding_service: EmbeddingInterface = Depends(get_embedding_service),
    index_service: IndexInterface = Depends(get_indexing_service),
    reranker_service: RerankerInterface = Depends(get_reranker_service),
    llm_service: LLMInterface = Depends(get_llm_service),
) -> QueryProcessor:
    """Returns an instance of the QueryProcessor with all required services."""
    return QueryProcessor(
        embedding_service=embedding_service,
        index_service=index_service,
        reranker_service=reranker_service,
        llm_service=llm_service,
        score_threshold=settings.SCORE_THRESHOLD
    )