import asyncio
import os
from pprint import pprint

from api.dependencies.ai_dependencies import get_llm_service
from application.services.conversation_service import ConversationService
from application.services.context_management_service import ContextManagementService

from application.services.rag_context_retriever import RAGContextRetriever
from application.services.rag_explorer_services import RAGExplorer
from core.templates.templates import BASE_DIR
from core.use_cases.query import RAGQueryProcessor
from modules.llm import LLMFactory
from modules.storage.document_store import DocumentStore
from app.modules.embeding.embedding_factory import get_embedding_service
from domain.entities.document import Query

# Реальні залежності
from infrastructure.repositories.conversation_repository import ConversationRepository
from infrastructure.repositories.message_repository import MessageRepository
from infrastructure.repositories.conv_cont_repository import ConversationContextRepository
from infrastructure.repositories.document_repository import DocumentRepository

from app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Псевдо-користувач
current_user = type("User", (), {"id": "user-123"})()

async def main():
    # --- База та сесія ---
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    llm_services = get_llm_service()
    model_id = '0'

    if model_id is not None and model_id.isdigit():
        # Convert index to model name
        models = llm_services.list_available_models()
        print('list available models:' + str(models))
        index = int(model_id)
        if 0 <= index < len(models):

            model_id = models[index]["name"]
            print('model_id:' + str(model_id))
        else:
            # Handle invalid index
            model_id = None  # Use default model
    llm_service = llm_services.get_llm(model_id)
    async with async_session() as db:
        # --- Репозиторії ---

        print('Starting')
        conversation_repo = ConversationRepository(db)
        message_repo = MessageRepository(db)
        context_repo = ConversationContextRepository(db)
        document_repo = DocumentRepository(db)

        print('Сервіси')
        # --- Сервіси ---
        embedding_service = await get_embedding_service()

        BASE_DIR = os.path.abspath(os.path.dirname(__file__))

        ABS_PATH = BASE_DIR + '/data' + '/processed'
        document_store = DocumentStore(document_repo, embedding_service, storage_path=ABS_PATH)
        rag_explorer = RAGExplorer(document_store)
        conversation_service = ConversationService(conversation_repo, message_repo)
        context_service = ContextManagementService(context_repo, message_repo, embedding_service, llm_service)
        rag_context_retriever = RAGContextRetriever(
            vector_index_service=document_store,
            context_service=context_service,
            conversation_service=conversation_service
        )
        print('Тестова розмова')
        message = "МЕТА І ЗАВДАННЯ КВАЛІФІКАЦІЙНОЇ РОБОТИ"
        # --- Тестова розмова ---
        # conversation = await conversation_service.create_conversation(user_id='b7507654-117d-4337-8f76-a8d93359d5d3')
        # conversation_id = conversation.id
        #
        # print('Add message:', message)
        # await conversation_service.add_message(
        #     conversation_id=conversation_id,
        #     role="user",
        #     content=message
        # )

        # --- RAG Query ---
        print('start RAG processing')
        query_processor = RAGQueryProcessor(
            document_store=document_store,
            embedding_service=embedding_service,
            llm_provider=llm_service,
            rag_context_retriever=rag_context_retriever,
            rag_explorer=rag_explorer
        )
        print('start RAG process_query')
        result = await query_processor.process_query(
            Query(text=message),
            owner_id='b7507654-117d-4337-8f76-a8d93359d5d3',
            theme_id='7cc621b9-e6d8-44e1-a0ae-8ff46a7ade1c'
        )

        assistant_response = result["response"]
        print('start conversation_service.add_messag')
        # await conversation_service.add_message(
        #
        #     role="assistant",
        #     content=assistant_response if isinstance(assistant_response, str) else assistant_response.get("text", "")
        # )

        print("🧠 ASSISTANT REPLY:")
        pprint(result)

if __name__ == "__main__":
    asyncio.run(main())
