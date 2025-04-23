from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from pydantic import parse_obj_as

from api.schemas.conversation import MessageResponse
from app.infrastructure.database.db_models import Conversation, Message
from infrastructure.repositories.conversation_repository import ConversationRepository
from app.modules.llm.factory import LLMFactory
from domain.interfaces.llm import LLMInterface


class ConversationService:
    """
    Async Service layer for managing conversations and their messages.

    Attributes
    ----------
    conversation_repo : ConversationRepository
        Repository for conversation database operations.
    message_repo : MessageRepository
        Repository for message database operations.

    """

    def __init__(self, conversation_repo, message_repo):
        """
        Initialize the ConversationService with repositories and an LLM service.

        Parameters
        ----------
        conversation_repo : ConversationRepository
            The repository for managing conversations.
        message_repo : MessageRepository
            The repository for managing messages.
        llm_service : BaseLLMService
            The service for generating content using LLMs.
        """
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self._llm_cache = {}  # Cache for LLM instances by model ID

    async def create_conversation(self, user_id: str, title: str = "New Conversation", theme_id: Optional[str] = None,
                                  model_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> \
            Optional[Conversation]:
        """
        Create a new conversation for a user.

        Parameters
        ----------
        user_id : str
            Unique identifier of the user.
        title : str, optional
            Title of the conversation (default is "New Conversation").
        theme_id : Optional[str], optional
            ID of the knowledge theme for this conversation.
        model_id : Optional[str], optional
            ID of the AI model to use.
        metadata : Optional[Dict[str, Any]], optional
            Additional conversation metadata.

        Returns
        -------
        Optional[Conversation]
            The newly created conversation object, or None if creation failed.
        """
        conversation = Conversation(user_id=user_id, title=title, theme_id=theme_id, model_id=model_id)
        if metadata:
            conversation.metadata_dict = metadata
        return await self.conversation_repo.create(conversation)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation by its ID.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.

        Returns
        -------
        Optional[Conversation]
            The conversation object if found, None otherwise.
        """
        return await self.conversation_repo.get_by_id(conversation_id)

    async def update_conversation(self, conversation_id: str, title: Optional[str] = None,
                                  is_active: Optional[bool] = None,
                                  metadata: Optional[Dict[str, Any]] = None, model_id: Optional[str] = None) -> \
    Optional[Conversation]:
        """
        Update a conversation's properties.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.
        title : Optional[str], optional
            New title for the conversation.
        is_active : Optional[bool], optional
            New active status for the conversation.
        metadata : Optional[Dict[str, Any]], optional
            Additional metadata to update or add.
        model_id : Optional[str], optional
            New model ID to use for this conversation.

        Returns
        -------
        Optional[Conversation]
            The updated conversation object, or None if update failed.
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None

        if title is not None:
            conversation.title = title
        if is_active is not None:
            conversation.is_active = is_active
        if model_id is not None:
            conversation.model_id = model_id
        if metadata is not None:
            current_metadata = conversation.metadata_dict or {}
            current_metadata.update(metadata)
            conversation.metadata_dict = current_metadata

        return await self.conversation_repo.update(conversation)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.

        Returns
        -------
        bool
            True if the conversation was deleted, False otherwise.
        """
        return await self.conversation_repo.delete(conversation_id)

    async def add_message(self, conversation_id: str, role: str, content: str, tokens: int = 0, is_hidden: bool = False,
                          references: Optional[List[Dict[str, Any]]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> \
            Optional[Message]:
        """
        Add a new message to a conversation.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.
        role : str
            Role of the message sender (user, assistant, system).
        content : str
            Content of the message.
        tokens : int, optional
            Number of tokens in the message (default is 0).
        is_hidden : bool, optional
            Flag indicating if the message should be hidden (default is False).
        references : Optional[List[Dict[str, Any]]], optional
            List of references associated with the message.
        metadata : Optional[Dict[str, Any]], optional
            Additional message metadata.

        Returns
        -------
        Optional[Message]
            The created message object, or None if creation failed.
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None

        message = Message(conversation_id=conversation_id, role=role, content=content, tokens=tokens,
                          is_hidden=is_hidden)
        if references:
            message.references_list = references
        if metadata:
            message.metadata_dict = metadata

        # Track message count in conversation metadata
        if conversation.conversation_metadata is None:
            conversation.conversation_metadata = {}

        msg_count = conversation.conversation_metadata.get("message_count", 0) + 1
        conversation.conversation_metadata["message_count"] = msg_count
        conversation.conversation_metadata["last_activity"] = datetime.now().isoformat()

        await self.conversation_repo.update(conversation)

        return await self.message_repo.create(message)

    async def get_messages(self, conversation_id: str, include_hidden: bool = False,
                           limit: Optional[int] = None, offset: Optional[int] = None) -> List[Message]:
        """
        Get messages in a conversation with optional pagination.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.
        include_hidden : bool, optional
            If True, include hidden messages (default is False).
        limit : Optional[int], optional
            Maximum number of messages to return.
        offset : Optional[int], optional
            Number of messages to skip.

        Returns
        -------
        List[Message]
            List of messages in the conversation.
        """
        return await self.message_repo.get_by_conversation_id(
            conversation_id,
            include_hidden=include_hidden,
            limit=limit,
            offset=offset
        )

    async def generate_title(self, conversation_id: str) -> Optional[str]:
        """
        Generate a title for a conversation based on its initial messages.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.

        Returns
        -------
        Optional[str]
            Generated title if successful, None otherwise.
        """
        messages = await self.get_messages(conversation_id)
        if not messages or len(messages) < 2:
            return None

        content = "\n".join([f"{msg.role}: {msg.content}" for msg in messages[:3]])
        prompt = f"Generate a short, concise title (5 words or less) for this conversation:\n\n{content}"

        try:
            # Get the conversation's specific model if available
            llm = await self._get_llm_for_conversation(conversation_id)
            title = await llm.generate_text(prompt)
            title = title.strip()
            conversation = await self.get_conversation(conversation_id)
            if conversation:
                conversation.title = title
                await self.conversation_repo.update(conversation)
            return title
        except Exception:
            return None

    async def deactivate_conversation(self, conversation_id: str) -> bool:
        """
        Deactivate a conversation without deleting it.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.

        Returns
        -------
        bool
            True if the conversation was deactivated, False otherwise.
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False
        conversation.is_active = False
        conversation.metadata_dict = conversation.metadata_dict or {}
        conversation.metadata_dict["deactivated_at"] = datetime.now().isoformat()
        await self.conversation_repo.update(conversation)
        return True

    async def reactivate_conversation(self, conversation_id: str) -> bool:
        """
        Reactivate a previously deactivated conversation.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.

        Returns
        -------
        bool
            True if the conversation was reactivated, False otherwise.
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False
        conversation.is_active = True
        conversation.metadata_dict = conversation.metadata_dict or {}
        conversation.metadata_dict["reactivated_at"] = datetime.now().isoformat()
        await self.conversation_repo.update(conversation)
        return True

    async def clear_messages(self, conversation_id: str) -> bool:
        """
        Delete all messages from a conversation.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.

        Returns
        -------
        bool
            True if all messages were deleted, False otherwise.
        """
        messages = await self.get_messages(conversation_id)
        if not messages:
            return False

        for message in messages:
            await self.message_repo.delete(message.id)

        # Reset message count in conversation metadata
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.metadata_dict = conversation.metadata_dict or {}
            conversation.metadata_dict["message_count"] = 0
            conversation.metadata_dict["cleared_at"] = datetime.now().isoformat()
            await self.conversation_repo.update(conversation)

        return True

    async def get_user_conversations(self, user_id: str, active_only: bool = False,
                                     limit: Optional[int] = None, offset: Optional[int] = None,
                                     sort_by: str = "updated_at", sort_dir: str = "desc") -> List[Conversation]:
        """
        Retrieve conversations for a specific user with pagination and sorting.

        Parameters
        ----------
        user_id : str
            The unique identifier of the user.
        active_only : bool, optional
            If True, only active conversations will be retrieved (default is False).
        limit : Optional[int], optional
            Maximum number of conversations to return.
        offset : Optional[int], optional
            Number of conversations to skip.
        sort_by : str, optional
            Field to sort by (default is "updated_at").
        sort_dir : str, optional
            Sort direction: "asc" or "desc" (default is "desc").

        Returns
        -------
        List[Conversation]
            A list of Conversation objects associated with the user.
        """
        return await self.conversation_repo.get_by_user_id(
            user_id,
            active_only=active_only,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir
        )

    async def search_conversations(self, user_id: str, search_term: str,
                                   limit: Optional[int] = None, offset: Optional[int] = None) -> List[Conversation]:
        """
        Search conversations by title and content for a specific user.

        Parameters
        ----------
        user_id : str
            The unique identifier of the user.
        search_term : str
            Term to search for in conversation titles and message content.
        limit : Optional[int], optional
            Maximum number of conversations to return.
        offset : Optional[int], optional
            Number of conversations to skip.

        Returns
        -------
        List[Conversation]
            A list of matching Conversation objects.
        """
        return await self.conversation_repo.search(
            user_id=user_id,
            search_term=search_term,
            limit=limit,
            offset=offset
        )

    async def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return {}

        messages = await self.get_messages(conversation_id, include_hidden=True)

        # Count messages by role
        role_counts = {}
        total_tokens = 0
        for msg in messages:
            role_counts[msg.role] = role_counts.get(msg.role, 0) + 1
            total_tokens += msg.tokens

        first_message_time = messages[0].created_at if messages else None
        last_message_time = messages[-1].created_at if messages else None

        return {
            "id": conversation.id,
            "title": conversation.title,
            "user_id": conversation.user_id,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "is_active": conversation.is_active,
            "theme_id": conversation.theme_id,
            "model_id": conversation.model_id,
            "metadata": conversation.conversation_metadata,
            "message_count": len(messages),
            "role_distribution": role_counts,
            "total_tokens": total_tokens,
            "first_message": first_message_time.isoformat() if first_message_time else None,
            "last_message": last_message_time.isoformat() if last_message_time else None,
            "messages": messages,
        }

    async def _get_llm_for_conversation(self, conversation_id: str) -> LLMInterface:
        """
        Get the appropriate LLM for a specific conversation.

        Uses the conversation's model_id if available, otherwise falls back to default.

        Parameters
        ----------
        conversation_id : str
            Unique identifier of the conversation.

        Returns
        -------
        LLMInterface
            LLM interface instance.
        """
        conversation = await self.get_conversation(conversation_id)
        model_id = conversation.model_id if conversation else None

        # Use cached LLM if available
        if model_id and model_id in self._llm_cache:
            return self._llm_cache[model_id]

        # Create new LLM instance
        llm = LLMFactory.get_llm(model_id)

        # Cache for future use
        if model_id:
            self._llm_cache[model_id] = llm

        return llm

    async def fork_conversation(self, conversation_id: str, user_id: str,
                                new_title: Optional[str] = None) -> Optional[Tuple[Conversation, List[Message]]]:
        """
        Create a fork/copy of an existing conversation.

        Parameters
        ----------
        conversation_id : str
            ID of the conversation to fork.
        user_id : str
            ID of the user creating the fork.
        new_title : Optional[str], optional
            Title for the new conversation. If None, will append "(Fork)" to original title.

        Returns
        -------
        Optional[Tuple[Conversation, List[Message]]]
            Tuple of (new conversation, copied messages), or None if fork failed.
        """
        # Get original conversation
        original = await self.get_conversation(conversation_id)
        if not original:
            return None

        # Create new conversation
        title = new_title or f"{original.title} (Fork)"
        metadata = original.metadata_dict.copy() if original.metadata_dict else {}
        metadata["forked_from"] = conversation_id
        metadata["forked_at"] = datetime.now().isoformat()

        new_conversation = await self.create_conversation(
            user_id=user_id,
            title=title,
            theme_id=original.theme_id,
            model_id=original.model_id,
            metadata=metadata
        )

        if not new_conversation:
            return None

        # Copy messages
        original_messages = await self.get_messages(conversation_id)
        new_messages = []

        for msg in original_messages:
            new_msg = await self.add_message(
                conversation_id=new_conversation.id,
                role=msg.role,
                content=msg.content,
                tokens=msg.tokens,
                is_hidden=msg.is_hidden,
                references=msg.references_list,
                metadata=msg.metadata_dict
            )
            if new_msg:
                new_messages.append(new_msg)

        return new_conversation, new_messages