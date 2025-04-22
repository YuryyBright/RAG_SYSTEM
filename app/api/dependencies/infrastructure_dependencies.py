from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from domain.interfaces.reranking import RerankingService
from infrastructure.repositories import get_async_db
from infrastructure.repositories.conversation_repository import ConversationRepository
from infrastructure.repositories.message_repository import MessageRepository
from infrastructure.repositories.document_repository import DocumentRepository
from infrastructure.repositories.file_repository import FileRepository
from infrastructure.repositories.theme_repository import ThemeRepository
from infrastructure.repositories.conv_cont_repository import ConversationContextRepository
from application.services.task_services import TaskManager
from modules.reranking.factory import RerankerFactory


def get_conversation_repository(db: AsyncSession = Depends(get_async_db)) -> ConversationRepository:
    return ConversationRepository(db)

def get_message_repository(db: AsyncSession = Depends(get_async_db)) -> MessageRepository:
    return MessageRepository(db)

def get_document_repository(db: AsyncSession = Depends(get_async_db)) -> DocumentRepository:
    return DocumentRepository(db)

def get_file_repository(db: AsyncSession = Depends(get_async_db)) -> FileRepository:
    return FileRepository(db)

def get_theme_repository(db: AsyncSession = Depends(get_async_db)) -> ThemeRepository:
    return ThemeRepository(db)

def get_context_repository(db: AsyncSession = Depends(get_async_db)) -> ConversationContextRepository:
    return ConversationContextRepository(db)

def get_task_manager(db: AsyncSession = Depends(get_async_db)) -> TaskManager:
    return TaskManager(db)

def get_reranker() -> RerankingService:
    return RerankerFactory.get_reranker(settings.RERANKER_TYPE)