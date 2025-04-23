import asyncio

from api.dependencies.ai_dependencies import get_llm_service
from application.services.conversation_service import ConversationService
from application.services.context_management_service import ContextManagementService

from application.services.rag_context_retriever import RAGContextRetriever
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

    llm_services = LLMFactory()
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


        document_store = DocumentStore(document_repo, embedding_service, storage_path=settings.DOCUMENT_STORAGE_PATH)

        conversation_service = ConversationService(conversation_repo, message_repo)
        context_service = ContextManagementService(context_repo, message_repo, embedding_service, llm_service)
        rag_context_retriever = RAGContextRetriever(
            vector_index_service=document_store,
            context_service=context_service,
            conversation_service=conversation_service
        )
        print('Тестова розмова')
        # --- Тестова розмова ---
        conversation = await conversation_service.create_conversation(user_id=current_user.id)
        conversation_id = conversation.id
        message = "Що ти знаєш про мої документи?"
        print('Add message:', message)
        await conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message
        )

        # --- RAG Query ---
        print('start RAG processing')
        query_processor = RAGQueryProcessor(
            document_store=document_store,
            embedding_service=embedding_service,
            llm_provider=llm_service,
            rag_context_retriever=rag_context_retriever
        )
        print('start RAG process_query')
        result = await query_processor.process_query(
            Query(text=message),
            conversation_id=conversation_id,
            theme_id='bae54c67-fe50-4e75-81f2-85086cfa8c12'
        )

        assistant_response = result["response"]
        print('start conversation_service.add_messag')
        await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_response if isinstance(assistant_response, str) else assistant_response.get("text", "")
        )

        print("🧠 ASSISTANT REPLY:")
        print(assistant_response)

if __name__ == "__main__":
    asyncio.run(main())
