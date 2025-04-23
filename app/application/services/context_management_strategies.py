import json
from typing import List, Optional, Any
from datetime import datetime

from infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.database.db_models import ConversationContext, Message


from infrastructure.repositories.conv_cont_repository import ConversationContextRepository
from modules.llm.base import BaseLLM
from utils.logger_util import get_logger

logger = get_logger(__name__)

class ConversationSummarizer:
    """
    Asynchronous strategy for conversation summarization to maintain long-term context.

    Methods:
        create_summary: Summarize recent messages and persist as a context entry.
        create_progressive_summary: Consolidate previous summaries into a higher-level summary.
        extra_functionality: Placeholder for extending summarization logic.
    """

    def __init__(
            self,
            context_repo: ConversationContextRepository,
            message_repo: MessageRepository,
            llm_service: BaseLLM,
    ):
        self.context_repo = context_repo
        self.message_repo = message_repo
        self.llm_service = llm_service

    async def create_summary(
            self,
            conversation_id: str,
            message_count: int = 10,
            summary_priority: int = 10,
    ) -> Optional[ConversationContext]:
        """
        Asynchronously create a summary of the most recent messages.

        Args:
            conversation_id: ID of the conversation to summarize.
            message_count: Number of recent messages to include.
            summary_priority: Priority level for the summary entry.

        Returns:
            The created ConversationContext or None on failure.
        """
        try:
            messages: List[Message] = await self.message_repo.get_by_conversation_id(
                conversation_id, include_hidden=False
            )[-message_count:]

            if not messages:
                return None

            message_text = "\n".join(f"{msg.role}: {msg.content}" for msg in messages)
            prompt = (
                "Summarize this conversation segment concisely while preserving key information:\n\n"
                f"{message_text}\n\nSummary:"
            )

            summary_text = await self.llm_service.generate_text(prompt)

            # Serialize only JSON-compatible data
            metadata = {
                "message_ids": [str(msg.id) for msg in messages],  # Ensure IDs are strings
                "message_count": len(messages),
                "start_time": messages[0].created_at.isoformat() if messages else None,
                "end_time": messages[-1].created_at.isoformat() if messages else None,
            }

            context = ConversationContext(
                conversation_id=conversation_id,
                context_type="summary",
                content=summary_text,
                priority=summary_priority,
                metadata=json.dumps(metadata),
            )
            return await self.context_repo.create(context)
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}", exc_info=True)
            return None

    async def create_progressive_summary(
            self,
            conversation_id: str,
    ) -> Optional[ConversationContext]:
        """
        Asynchronously consolidate individual summaries into a progressive summary.

        Args:
            conversation_id: ID of the conversation.

        Returns:
            The new consolidated ConversationContext or None.
        """
        try:
            summaries = await self.context_repo.get_by_conversation_id(
                conversation_id=conversation_id,
                context_type="summary",
                limit=3,
                order_by_priority=True,
            )

            if not summaries or len(summaries) < 2:
                return None

            combined_text = "\n\n".join(s.content for s in summaries)
            prompt = (
                "Create a consolidated summary from these individual conversation summaries:\n\n"
                f"{combined_text}\n\nConsolidated Summary:"
            )

            prog_text = await self.llm_service.generate_text(prompt)

            # Use consistent datetime format
            metadata = {
                "source_summary_ids": [str(s.id) for s in summaries],  # Ensure IDs are strings
                "created_at": datetime.now().isoformat(),
            }

            context = ConversationContext(
                conversation_id=conversation_id,
                context_type="progressive_summary",
                content=prog_text,
                priority=15,
                metadata=json.dumps(metadata),
            )
            return await self.context_repo.create(context)
        except Exception as e:
            logger.error(f"Error creating progressive summary: {str(e)}", exc_info=True)
            return None

class KeyPointsExtractor:
    """
    Asynchronous strategy to extract key points from conversation segments.

    Methods:
        extract_key_points: Extract and store key bullet points from recent messages.
        extra_functionality: Placeholder for extending extraction logic.
    """

    def __init__(
            self,
            context_repo: ConversationContextRepository,
            message_repo: MessageRepository,
            llm_service: BaseLLM,
    ):
        self.context_repo = context_repo
        self.message_repo = message_repo
        self.llm_service = llm_service

    async def extract_key_points(
            self,
            conversation_id: str,
            message_count: int = 5,
    ) -> Optional[ConversationContext]:
        """
        Asynchronously extract 3-5 key points from recent messages.

        Args:
            conversation_id: Conversation to analyze.
            message_count: Number of messages to include.

        Returns:
            Created ConversationContext with key points or None.
        """
        messages = await self.message_repo.get_by_conversation_id(
            conversation_id, include_hidden=False
        )[-message_count:]

        if not messages:
            return None

        text = "\n".join(f"{msg.role}: {msg.content}" for msg in messages)
        prompt = (
            "Extract 3-5 key points from this conversation segment that would be important to remember:\n\n"
            f"{text}\n\nKey Points:"
        )

        try:
            points = await self.llm_service.generate_text(prompt)
            context = ConversationContext(
                conversation_id=conversation_id,
                context_type="key_points",
                content=points,
                priority=8,
                metadata=json.dumps({
                    "message_ids": [msg.id for msg in messages],
                    "message_count": len(messages),
                }),
            )
            return await self.context_repo.create(context)
        except Exception as e:
            print(f"Error extracting key points: {e}")
            return None

    async def extra_functionality(
            self,
            conversation_id: str,
            **kwargs: Any,
    ) -> Any:
        """
        Placeholder for additional key-points extraction extensions.
        """
        raise NotImplementedError("`extra_functionality` is not implemented.")


class SlidingWindowManager:
    """
    Asynchronous strategy for managing a sliding window of contexts
    based on priority and age.

    Methods:
        maintain_window: Prune old or low-priority contexts to enforce limits.
        extra_functionality: Placeholder for additional window behaviors.
    """

    def __init__(
            self,
            context_repo: ConversationContextRepository,
    ):
        self.context_repo = context_repo

    async def maintain_window(
            self,
            conversation_id: str,
            max_contexts: int = 20,
            min_high_priority: int = 5,
    ) -> None:
        """
        Enforce a maximum number of contexts, removing oldest low-priority first.

        Args:
            conversation_id: ID of the conversation.
            max_contexts: Maximum contexts to keep.
            min_high_priority: Threshold for high-priority contexts.
        """
        try:
            contexts = await self.context_repo.get_by_conversation_id(conversation_id)
            if len(contexts) <= max_contexts:
                return

            high = [c for c in contexts if c.priority >= min_high_priority]
            low = [c for c in contexts if c.priority < min_high_priority]
            to_remove = len(contexts) - max_contexts

            # Sort by both priority (ascending) and created_at (ascending)
            # This ensures consistent removal order
            low.sort(key=lambda c: (c.priority, c.created_at))

            # Track deletion results
            deletion_results = []

            if len(low) >= to_remove:
                for c in low[:to_remove]:
                    result = await self.context_repo.delete(c.id)
                    deletion_results.append(result)
            else:
                for c in low:
                    result = await self.context_repo.delete(c.id)
                    deletion_results.append(result)
                    to_remove -= 1
                if to_remove > 0:
                    high.sort(key=lambda c: (c.priority, c.created_at))
                    for c in high[:to_remove]:
                        result = await self.context_repo.delete(c.id)
                        deletion_results.append(result)

            # Check if any deletions failed
            if False in deletion_results:
                logger.warning(f"Some context deletions failed for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error maintaining context window: {str(e)}", exc_info=True)

    async def extra_functionality(
            self,
            conversation_id: str,
            **kwargs: Any,
    ) -> Any:
        """
        Placeholder for additional sliding window behaviors (e.g., archiving).
        """
        raise NotImplementedError("`extra_functionality` is not implemented.")


class SemanticContextSearcher:
    """
    Asynchronous strategy for finding semantically relevant context entries.

    Methods:
        find_relevant_context: Retrieve context entries matching a query embedding.
        extra_functionality: Placeholder for additional search extensions.
    """

    def __init__(
            self,
            context_repo: ConversationContextRepository,
            embedding_service: Any,
    ):
        self.context_repo = context_repo
        self.embedding_service = embedding_service

    async def find_relevant_context(
            self,
            conversation_id: str,
            query: str,
            limit: int = 5,
    ) -> List[ConversationContext]:
        """
        Asynchronously find semantically relevant contexts for a query.

        Args:
            conversation_id: Conversation to search.
            query: Query text.
            limit: Maximum contexts to return.

        Returns:
            List of ConversationContext entries.
        """
        embedding = await self.embedding_service.get_embedding(query)
        results = await self.context_repo.semantic_search(
            conversation_id=conversation_id,
            query_embedding=embedding,
            limit=limit,
        )
        return results

    async def extra_functionality(
            self,
            conversation_id: str,
            **kwargs: Any,
    ) -> Any:
        """
        Placeholder for extending semantic search (e.g., caching layers).
        """
        raise NotImplementedError("`extra_functionality` is not implemented.")