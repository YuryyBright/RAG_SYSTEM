from fastapi import Depends

from api.dependencies.ai_dependencies import get_vector_index
from api.dependencies.document_dependency import get_document_store, get_file_manager, get_file_processor, \
    get_chunking_service
from api.dependencies.infrastructure_dependencies import get_theme_repository
from api.websockets.task_updates import get_task_update_manager
from app.core.use_cases.theme import ThemeUseCase
from app.core.use_cases.file_processing import FileProcessingUseCase, FileProcessor
from application.services.chunking_service import ChunkingService
from modules.embeding.embedding_factory import get_embedding_service


def get_theme_use_case(
    theme_repository=Depends(get_theme_repository),
    document_store=Depends(get_document_store),
    file_manager=Depends(get_file_manager),
) -> ThemeUseCase:
    return ThemeUseCase(theme_repository, document_store, file_manager)

async def file_processing_use_case(
    file_processor: FileProcessor = Depends(get_file_processor),
    chunking_service: ChunkingService = Depends(get_chunking_service),
    embedding_service = Depends(get_embedding_service),
    document_store = Depends(get_document_store),
    vector_index = Depends(get_vector_index),
    task_update_manager = Depends(get_task_update_manager)
) -> FileProcessingUseCase:
    return FileProcessingUseCase(
        file_processor,
        chunking_service,
        embedding_service,
        document_store,
        vector_index,
        task_update_manager
    )

# etc
