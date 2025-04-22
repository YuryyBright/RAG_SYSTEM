from typing import List, Dict, Any, Optional

from app.infrastructure.database.repository.message_repository import MessageRepository
from core.services.context_management_service import ContextManagementService


class RAGContextRetriever:
    """
    Service to retrieve relevant context from a conversation history
    for use in the RAG pipeline (asynchronous version).

    Methods:
        get_context_for_query: Asynchronously fetches recent messages, semantically relevant context,
            and the latest summary for a given conversation and query.
        format_context_for_llm: Formats retrieved context into a prompt-ready string.
        extra_functionality: Placeholder for additional asynchronous operations.
    """

    def __init__(
        self,
        context_service: ContextManagementService,
        message_repo: MessageRepository,
        recent_message_limit: int = 5,
        max_context_tokens: int = 2000,
    ):
        self.context_service = context_service
        self.message_repo = message_repo
        self.recent_message_limit = recent_message_limit
        self.max_context_tokens = max_context_tokens

    async def get_context_for_query(
        self, conversation_id: str, query: str
    ) -> Dict[str, Any]:
        """
        Asynchronously retrieve context for a query in a specific conversation.

        Returns a dict with:
            - recent_messages: List of the most recent messages (role and content).
            - relevant_context: List of semantically relevant context entries with type and content.
            - summary: The latest conversation summary, if available.
        """
        result: Dict[str, Any] = {
            "recent_messages": [],
            "relevant_context": [],
            "summary": None,
        }

        # Fetch recent messages asynchronously
        all_messages = await self.message_repo.get_by_conversation_id(
            conversation_id, include_hidden=False
        )
        recent = all_messages[-self.recent_message_limit:]
        result["recent_messages"] = [
            {"role": msg.role, "content": msg.content} for msg in recent
        ]

        # Fetch semantically relevant context asynchronously
        relevant_contexts = await self.context_service.get_relevant_context(
            conversation_id=conversation_id, query=query, limit=5
        )
        result["relevant_context"] = [
            {"type": ctx.context_type, "content": ctx.content}
            for ctx in relevant_contexts
        ]

        # Fetch the most recent summary, if any
        summaries = await self.context_service.context_repo.get_by_conversation_id(
            conversation_id=conversation_id,
            context_type="summary",
            limit=1,
        )
        if summaries:
            result["summary"] = summaries[0].content

        return result

    def format_context_for_llm(self, context_data: Dict[str, Any]) -> str:
        """
        Format retrieved context into a string for inclusion in the LLM prompt.

        Steps:
            1. Include a conversation summary if available.
            2. List semantically relevant context entries.
            3. Append recent message history.

        Returns:
            A string combining all context sections separated by newlines.
        """
        formatted_parts: List[str] = []

        # Add summary section
        if context_data.get("summary"):
            formatted_parts.append(
                f"CONVERSATION SUMMARY:\n{context_data['summary']}\n"
            )

        # Add relevant context entries
        if context_data.get("relevant_context"):
            formatted_parts.append("RELEVANT CONTEXT:")
            for ctx in context_data["relevant_context"]:
                formatted_parts.append(f"{ctx['type'].upper()}: {ctx['content']}")
            formatted_parts.append("")

        # Add recent conversation messages
        if context_data.get("recent_messages"):
            formatted_parts.append("RECENT CONVERSATION:")
            for msg in context_data["recent_messages"]:
                formatted_parts.append(f"{msg['role'].upper()}: {msg['content']}")

        return "\n".join(formatted_parts)

    async def extra_functionality(
        self, conversation_id: str, **kwargs: Any
    ) -> Any:
        """
        Placeholder for additional asynchronous functionality.

        Implement custom behavior here, for example:
            - Persisting extended context
            - Triggering external notifications
            - Post-processing retrieved context

        Args:
            conversation_id: The ID of the conversation.
            **kwargs: Optional parameters for customization.

        Returns:
            Result of the extra functionality.

        Raises:
            NotImplementedError: This method should be implemented by subclasses or via monkey-patching.
        """
        raise NotImplementedError(
            "`extra_functionality` is not yet implemented."
        )
