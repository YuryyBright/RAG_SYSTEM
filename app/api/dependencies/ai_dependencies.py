from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.infrastructure_dependencies import get_conversation_repository, get_message_repository, \
    get_context_repository, get_reranker
from app.modules.embeding.embedding_factory import get_embedding_service
from app.modules.indexing.faiss_hnsw import FaissVectorIndex
from app.modules.indexing.chroma_index import ChromaVectorIndex
from app.modules.indexing.milvus import MilvusVectorIndex
from app.modules.llm.factory import LLMFactory
from app.modules.reranking.factory import RerankerFactory
from application.services.context_management_service import ContextManagementService
from application.services.conversation_service import ConversationService
from application.services.llm_service import LLMService
from app.config import settings
from application.services.rag_context_retriever import RAGContextRetriever

from domain.interfaces.indexing import IndexInterface
from domain.interfaces.reranking import RerankingService
from infrastructure.repositories import get_async_db
from infrastructure.repositories.conv_cont_repository import ConversationContextRepository
from infrastructure.repositories.conversation_repository import ConversationRepository
from infrastructure.repositories.message_repository import MessageRepository


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

def get_llm_service() -> LLMFactory:
    return LLMFactory()

def get_reranker_service() -> RerankingService:
    return RerankerFactory.get_reranker(reranker_type=settings.RERANKER_TYPE)


def get_conversation_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
):
    """Get conversation service dependency."""
    return ConversationService(conversation_repo, message_repo)

def get_context_service(
    context_repo: ConversationContextRepository = Depends(get_context_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    embedding_service = Depends(get_embedding_service),
    llm_service_ = Depends(get_llm_service),
    max_context_window: int = 20
):
    """Get context management service dependency."""
    return ContextManagementService(
        context_repo,
        message_repo,
        embedding_service,
        llm_service_,
        max_context_window
    )

def get_rag_context_retriever(
    vector_index_service=Depends(get_vector_index),
    context_service=Depends(get_context_service),
    conversation_service=Depends(get_conversation_service),
    reranker=Depends(get_reranker)
):
    return RAGContextRetriever(
        vector_index_service=vector_index_service,
        context_service=context_service,
        conversation_service=conversation_service,
        reranker=reranker
    )