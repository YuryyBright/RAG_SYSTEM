# """
# Dependency Injection Providers for FastAPI.
#
# This module configures the DI system for:
# - Repositories (Document, Theme)
# - Services (Embedding, Indexing, Reranking, LLM)
# - Use Cases (Theme, QueryProcessor)
# """
# from typing import Annotated
#
# from fastapi import Depends
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from application.services.auth_service import AuthService
# from application.services.conversation_service import ConversationService
# from domain.interfaces.document_store import DocumentStoreInterface
# from infrastructure.repositories.repository.conv_cont_repository import ConversationContextRepository
# from infrastructure.repositories.repository.conversation_repository import ConversationRepository
# from infrastructure.repositories.repository.document_repository import DocumentRepository
# from infrastructure.repositories.repository.file_repository import FileRepository
# from infrastructure.repositories.repository.message_repository import MessageRepository
# from infrastructure.repositories.repository.theme_repository import ThemeRepository
# from modules.embeding.embedding_factory import get_embedding_service
# from modules.indexing.chroma_index import ChromaVectorIndex
# from modules.indexing.milvus import MilvusVectorIndex
# from modules.llm.factory import LLMFactory
# from modules.reranking.factory import RerankerFactory
# from modules.storage.file_manager import FileManager
#
# # Fix typo in import path
#
# from app.config import settings
#
# # Core Interfaces
# from domain.interfaces.embedding import EmbeddingInterface
# from domain.interfaces.indexing import IndexInterface
# from domain.interfaces.llm import LLMInterface
#
# from app.core.use_cases.file_processing import FileProcessingUseCase, FileProcessor
#
# # Use Cases
# from app.core.use_cases.theme import ThemeUseCase
#
# # Adapters
# from app.modules.storage.document_store import DocumentStore
# from app.modules.indexing.faiss_hnsw import FaissVectorIndex
#
# # Infrastructure
#
#
# from infrastructure.repositories.repository import get_async_db
# from app.utils.logger_util import get_logger
# from domain.interfaces.reranking import RerankingService
# from application.services.chunking_service import ChunkingService
# from application.services.context_management_service import ContextManagementService
#
# from application.services.llm_service import LLMService
# from application.services.rag_context_retriever import RAGContextRetriever
#
# from application.services.task_services import TaskManager
# from application.services.vector_index_services import VectorIndexService
# from api.websockets.task_updates import get_task_update_manager, TaskUpdateManager
#
# logger = get_logger(__name__)
#
#
# # === Infrastructure ===
# # async def get_cache_service() -> RedisCache:
# #     """
# #     Provides the Redis cache service.
# #
# #     This dependency is used to inject the cache service into other
# #     services that need caching functionality.
# #
# #     Returns:
# #         RedisCache: The configured Redis cache service
# #     """
# #     return await get_redis_cache()
#
#
# def get_document_repository(db: AsyncSession = Depends(get_async_db)) -> DocumentRepository:
#     """Provides DocumentRepository bound to a DB session."""
#     return DocumentRepository(db)
#
#
# def get_task_manager(db: AsyncSession = Depends(get_async_db)) -> TaskManager:
#     """Helper to provide a TaskManager with a DB session."""
#     return TaskManager(db)
#
#
# def get_auth_service(db: AsyncSession = Depends(get_async_db)) -> AuthService:
#     """
#     A FastAPI dependency that returns an AuthService with a real AsyncSession.
#     """
#     return AuthService(db)
#
#
# def get_theme_repository(db: AsyncSession = Depends(get_async_db)) -> ThemeRepository:
#     """Provides ThemeRepository bound to a DB session."""
#     return ThemeRepository(db)
#
#
# def get_file_manager() -> FileManager:
#     """Return a new FileManager instance."""
#     return FileManager()
# # === Embedding / Model Services ===
#
#
#
#
#
# def get_reranker_service() -> RerankingService:
#     """Provides reranker model interface."""
#     return RerankerFactory.get_reranker(reranker_type=settings.RERANKER_TYPE)
#
#
# # === Storage Services ===
#
# def get_document_store(
#         document_repository: DocumentRepository = Depends(get_document_repository),
#         embedding_service: EmbeddingInterface = Depends(get_embedding_service)
# ) -> DocumentStoreInterface:
#     """Provides a DocumentStore instance."""
#     return DocumentStore(
#         document_repository=document_repository,
#         embedding_service=embedding_service,
#         storage_path=settings.DOCUMENT_STORAGE_PATH
#     )
#
#
# def get_llm_service() -> LLMService:
#     """Dependency provider for the LLM service."""
#     # Create an instance that implements LLMInterface
#     # Using LLMFactory to get the default LLM implementation
#     llm_interface = LLMFactory.get_llm()
#
#     # Pass the interface to the LLMService constructor
#     return LLMService(llm_interface)
# # === Use Cases ===
#
# def get_theme_use_case_p(
#         theme_repository: ThemeRepository = Depends(get_theme_repository),
#         # document_store: DocumentStore = Depends(get_document_store),
#         # file_manager: FileManager = Depends(get_file_manager)
# ) -> ThemeUseCase:
#     """Provides the ThemeUseCase with repository + store dependencies."""
#     return ThemeUseCase(
#         theme_repository=theme_repository,
#         document_store=None,
#         file_manager=None
#     )
#
#
# def get_files_store(db: AsyncSession = Depends(get_async_db))-> FileRepository:
#     return FileRepository(db)
#
# def get_theme_use_case(
#         theme_repository: ThemeRepository = Depends(get_theme_repository),
#         document_store: DocumentStore = Depends(get_document_store),
#         file_manager: FileManager = Depends(get_file_manager)
# ) -> ThemeUseCase:
#     """Provides the ThemeUseCase with repository + store dependencies."""
#     return ThemeUseCase(
#         theme_repository=theme_repository,
#         document_store=document_store,
#         file_manager=file_manager
#     )
#
#
#
#
#
# async def get_chunking_service() -> ChunkingService:
#     """
#     Get chunking service instance.
#     """
#     # In a real implementation, you might need to pass configuration here
#     return ChunkingService()
#
#
#
#
#
# # def get_query_processor(
# #         embedding_service: EmbeddingInterface = Depends(get_embedding_service),
# #         index_service: IndexInterface = Depends(get_vector_index),
# #         reranker_service: RerankingService = Depends(get_reranker_service),
# #         llm_service: LLMInterface = Depends(get_llm_service)
# # ) -> QueryProcessor:
# #     """Provides a QueryProcessor instance with all AI services."""
# #     return QueryProcessor(
# #         embedding_service=embedding_service,
# #         index_service=index_service,
# #         reranker_service=reranker_service,
# #         llm_service=llm_service,
# #         score_threshold=settings.SCORE_THRESHOLD
# #     )
#
#
#
# def get_file_processor(db: AsyncSession = Depends(get_async_db)) -> FileProcessor:
#     file_repo = FileRepository(db)
#     return FileProcessor(file_repository=file_repo)
#
# async def file_processing_use_case(
#         file_processor: FileProcessor = Depends(get_file_processor),
#         chunking_service: ChunkingService = Depends(get_chunking_service),
#         embedding_service: EmbeddingInterface = Depends(get_embedding_service),
#         document_store: DocumentStore = Depends(get_document_store),
#         vector_index: VectorIndexService = Depends(get_vector_index),
#         task_update_manager: TaskUpdateManager = Depends(get_task_update_manager)
#
# ) -> FileProcessingUseCase:
#     """
#     Provides a FileProcessingUseCase instance via FastAPI's dependency injection.
#
#     This function injects all the required components:
#       - file_processor: Responsible for file reading/parsing
#       - embedding_service: For generating vector embeddings
#       - document_store: For persisting documents
#       - vector_index: For storing/retrieving vectors
#       - file_manager: For file storage / management tasks
#       - chunking_service:  For file CHUNKING / management tasks
#
#     Returns
#     -------
#     FileProcessingUseCase
#         A configured instance capable of processing and indexing files in the RAG pipeline.
#     """
#     return FileProcessingUseCase(
#         file_processor=file_processor,
#         chunking_service=chunking_service,
#         embedding_service=embedding_service,
#         document_store=document_store,
#         vector_index=vector_index,
#         task_update_manager = task_update_manager,
#     )
#
#
# # Conversation dependencies
# def get_conversation_repository(db: AsyncSession = Depends(get_async_db)):
#     """Get conversation repository dependency."""
#     return ConversationRepository(db)
#
# def get_message_repository(db: AsyncSession = Depends(get_async_db)):
#     """Get message repository dependency."""
#     return MessageRepository(db)
#
# def get_context_repository(db: AsyncSession = Depends(get_async_db)):
#     """Get conversation context repository dependency."""
#     return ConversationContextRepository(db)
#
# def get_conversation_service(
#     conversation_repo: ConversationRepository = Depends(get_conversation_repository),
#     message_repo: MessageRepository = Depends(get_message_repository),
# ):
#     """Get conversation service dependency."""
#     return ConversationService(conversation_repo, message_repo)
#
# def get_context_service(
#     context_repo: ConversationContextRepository = Depends(get_context_repository),
#     message_repo: MessageRepository = Depends(get_message_repository),
#     embedding_service = Depends(get_embedding_service),
#     llm_service_ = Depends(get_llm_service),
#     max_context_window: int = 20
# ):
#     """Get context management service dependency."""
#     return ContextManagementService(
#         context_repo,
#         message_repo,
#         embedding_service,
#         llm_service_,
#         max_context_window
#     )
# def get_llm_service() -> LLMInterface:
#     # You could also read a header or user‐choice from DB
#     return LLMFactory.get_llm()
#
# def get_reranker() -> RerankingService:
#     return RerankerFactory.get_reranker(settings.RERANKER_TYPE)
#
# # Update this function to include reranker
# def get_rag_context_retriever(
#     vector_index_service=Depends(get_vector_index),
#     context_service=Depends(get_context_service),
#     conversation_service=Depends(get_conversation_service),
#     reranker=Depends(get_reranker)
# ):
#     return RAGContextRetriever(
#         vector_index_service=vector_index_service,
#         context_service=context_service,
#         conversation_service=conversation_service,
#         reranker=reranker
#     )