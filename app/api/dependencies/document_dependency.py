from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.infrastructure_dependencies import get_document_repository
from application.services.chunking_service import ChunkingService
from config import settings
from domain.interfaces.document_store import DocumentStoreInterface
from domain.interfaces.embedding import EmbeddingInterface
from infrastructure.loaders.file_processor import FileProcessor
from infrastructure.repositories import get_async_db
from infrastructure.repositories.document_repository import DocumentRepository
from infrastructure.repositories.file_repository import FileRepository
from modules.embeding.embedding_factory import get_embedding_service
from modules.storage.document_store import DocumentStore
from modules.storage.file_manager import FileManager


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

def get_file_manager() -> FileManager:
    """Return a new FileManager instance."""
    return FileManager()

def get_file_processor(db: AsyncSession = Depends(get_async_db)) -> FileProcessor:
    file_repo = FileRepository(db)
    return FileProcessor(file_repository=file_repo)

async def get_chunking_service() -> ChunkingService:
    """
    Get chunking service instance.
    """
    # In a real implementation, you might need to pass configuration here
    return ChunkingService()