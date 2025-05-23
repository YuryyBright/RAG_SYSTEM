from typing import List, Optional, Dict, Any

from application.services.base_embedding_service import BaseEmbeddingService
from infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.database.db_models import ConversationContext

from infrastructure.repositories.conv_cont_repository import ConversationContextRepository
from modules.llm.base import BaseLLM
from utils.logger_util import get_logger


class ContextManagementService:
    """
    Async Service for managing conversation contexts using embeddings and LLM summarization.
    """

    def __init__(self, context_repo: ConversationContextRepository, message_repo: MessageRepository,
                 embedding_service: BaseEmbeddingService, llm_service: BaseLLM, max_context_window: int = 10):
        """
        Initialize the ContextManagementService.

        Parameters
        ----------
        context_repo : ConversationContextRepository
            Repository for managing conversation contexts.
        message_repo : MessageRepository
            Repository for managing messages.
        embedding_service : BaseEmbeddingService
            Service for generating embeddings.
        llm_service : BaseLLM
            Service for generating summaries using an LLM.
        max_context_window : int, optional
            Maximum allowed number of contexts to keep (default is 10).
        """
        self.context_repo = context_repo
        self.message_repo = message_repo
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.max_context_window = max_context_window

        # Add logger
        self.logger = get_logger(__name__)

    async def create_context(self, conversation_id: str, content: str, context_type: str = "message", priority: int = 1,
                             metadata: Optional[Dict[str, Any]] = None) -> Optional[ConversationContext]:
        """
        Create a context entry with embedding for a conversation.
        """
        try:
            embedding = await self.embedding_service.get_embedding(content)
            context = ConversationContext(
                conversation_id=conversation_id,
                context_type=context_type,
                content=content,
                embedding=embedding,
                priority=priority
            )
            if metadata:
                context.metadata_dict = metadata
            return await self.context_repo.create(context)
        except Exception as e:
            self.logger.error(f"Error creating context: {str(e)}", exc_info=True)
            return None

    async def summarize_conversation(self, conversation_id: str, message_limit: int = 20) -> Optional[
        ConversationContext]:
        """
        Create a summary context from recent conversation messages.
        """
        try:
            messages = await self.message_repo.get_by_conversation_id(conversation_id, include_hidden=False)
            if not messages:
                return None

            recent_messages = messages[-message_limit:] if len(messages) > message_limit else messages
            message_text = "\n".join([f"{msg.role}: {msg.content}" for msg in recent_messages])

            prompt = f"Summarize the key points of this conversation while preserving important details:\n\n{message_text}"

            summary = await self.llm_service.generate_text(prompt)
            return await self.create_context(
                conversation_id=conversation_id,
                content=summary,
                context_type="summary",
                priority=10,
                metadata={"message_count": len(recent_messages),
                          "start_time": recent_messages[0].created_at.isoformat() if recent_messages else None,
                          "end_time": recent_messages[-1].created_at.isoformat() if recent_messages else None}
            )
        except Exception as e:
            self.logger.error(f"Error summarizing conversation: {str(e)}", exc_info=True)
            return None

    async def maintain_context_window(self, conversation_id: str) -> None:
        """
        Maintain the context window by summarizing old messages and removing low-priority contexts.
        """
        try:
            all_contexts = await self.context_repo.get_by_conversation_id(conversation_id)
            if len(all_contexts) > self.max_context_window:
                # Sort by priority (high to low) then by updated_at (new to old)
                all_contexts.sort(key=lambda c: (-c.priority, -c.updated_at.timestamp() if c.updated_at else 0))

                # Keep the top contexts based on this combined sort
                to_keep = all_contexts[:self.max_context_window]
                to_delete = all_contexts[self.max_context_window:]

                # Delete the excess contexts
                for context in to_delete:
                    success = await self.context_repo.delete(context.id)
                    if not success:
                        self.logger.warning(f"Failed to delete context {context.id}")
        except Exception as e:
            self.logger.error(f"Error maintaining context window: {str(e)}", exc_info=True)

    async def extract_key_points(self, conversation_id: str, message_limit: int = 10) -> Optional[ConversationContext]:
        """
        Extract key points from recent conversation messages.
        """
        messages = await self.message_repo.get_by_conversation_id(conversation_id, include_hidden=False)
        messages = messages[-message_limit:]
        if not messages:
            return None

        message_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        prompt = f"Extract 3-5 key points from this conversation that would be important to remember for future reference:\n\n{message_text}"

        try:
            key_points = await self.llm_service.generate_text(prompt)
            return await self.create_context(
                conversation_id=conversation_id,
                content=key_points,
                context_type="key_points",
                priority=8,
                metadata={"message_count": len(messages)}
            )
        except Exception:
            return None

    async def get_relevant_context(self, conversation_id: str, query: str, limit: int = 5) -> List[ConversationContext]:
        """
        Get relevant context for a query using semantic search.
        """
        query_embedding = await self.embedding_service.get_embedding(query)
        results = await self.context_repo.semantic_search(conversation_id, query_embedding, limit)
        return results


    async def delete_context(self, context_id: str) -> bool:
        """
        Delete a single context by its ID.
        """
        return await self.context_repo.delete(context_id)

    async def list_contexts(self, conversation_id: str) -> List[ConversationContext]:
        """
        List all contexts associated with a conversation.
        """
        return await self.context_repo.get_by_conversation_id(conversation_id)

    async def update_context_priority(self, context_id: str, new_priority: int) -> Optional[ConversationContext]:
        """
        Update the priority of a context.
        """
        context = await self.context_repo.get_by_id(context_id)
        if not context:
            return None
        context.priority = new_priority
        return await self.context_repo.update(context)
