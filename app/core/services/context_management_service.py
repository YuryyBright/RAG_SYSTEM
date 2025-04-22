from typing import List, Optional, Dict, Any
import json
from datetime import datetime


from app.infrastructure.database.repository.message_repository import MessageRepository
from app.infrastructure.database.db_models import ConversationContext, Message

from app.adapters.llm.base_llm_service import BaseLLMService

from core.interfaces.base_embedding_service import BaseEmbeddingService
from infrastructure.database.repository.conv_cont_repository import ConversationContextRepository


class ContextManagementService:
    """
    Async Service for managing conversation contexts using embeddings and LLM summarization.
    """

    def __init__(self, context_repo: ConversationContextRepository, message_repo: MessageRepository, embedding_service: BaseEmbeddingService, llm_service: BaseLLMService, max_context_window: int = 10):
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
        llm_service : BaseLLMService
            Service for generating summaries using an LLM.
        max_context_window : int, optional
            Maximum allowed number of contexts to keep (default is 10).
        """
        self.context_repo = context_repo
        self.message_repo = message_repo
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.max_context_window = max_context_window

    async def create_context(self, conversation_id: str, content: str, context_type: str = "message", priority: int = 1, metadata: Optional[Dict[str, Any]] = None) -> Optional[ConversationContext]:
        """
        Create a context entry with embedding for a conversation.
        """
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

    async def summarize_conversation(self, conversation_id: str, message_limit: int = 20) -> Optional[ConversationContext]:
        """
        Create a summary context from recent conversation messages.
        """
        messages = await self.message_repo.get_by_conversation_id(conversation_id, include_hidden=False)
        if not messages:
            return None

        recent_messages = messages[-message_limit:] if len(messages) > message_limit else messages
        message_text = "\n".join([f"{msg.role}: {msg.content}" for msg in recent_messages])

        prompt = f"Summarize the key points of this conversation while preserving important details:\n\n{message_text}"

        try:
            summary = await self.llm_service.generate_text(prompt)
            return await self.create_context(
                conversation_id=conversation_id,
                content=summary,
                context_type="summary",
                priority=10,
                metadata={"message_count": len(recent_messages), "start_time": recent_messages[0].created_at.isoformat(), "end_time": recent_messages[-1].created_at.isoformat()}
            )
        except Exception:
            return None

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

    async def maintain_context_window(self, conversation_id: str) -> None:
        """
        Maintain the context window by summarizing old messages and removing low-priority contexts.
        """
        all_contexts = await self.context_repo.get_by_conversation_id(conversation_id)
        if len(all_contexts) > self.max_context_window:
            high_priority = [c for c in all_contexts if c.priority >= 5]
            low_priority = [c for c in all_contexts if c.priority < 5]
            low_priority.sort(key=lambda c: c.updated_at)

            to_keep = high_priority + low_priority[-(self.max_context_window - len(high_priority)):] if len(high_priority) < self.max_context_window else high_priority

            for context in all_contexts:
                if context not in to_keep:
                    await self.context_repo.delete(context.id)

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
