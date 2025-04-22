from typing import List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.infrastructure.database.db_models import Conversation
from utils.logger_util import get_logger

logger = get_logger(__name__)
class ConversationRepository:
    """
    Repository for managing Conversation entities in the database.

    Attributes
    ----------
    db_session : AsyncSession
        SQLAlchemy asynchronous session for database operations.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the repository with a database session.

        Parameters
        ----------
        db_session : AsyncSession
            SQLAlchemy asynchronous session for database operations.
        """
        self.db_session = db_session

    async def create(self, conversation: Conversation) -> Optional[Conversation]:
        """
        Create a new conversation in the database.

        Parameters
        ----------
        conversation : Conversation
            The Conversation object to be added to the database.

        Returns
        -------
        Optional[Conversation]
            The newly created Conversation object with updated fields, or None if failed.
        """
        try:
            self.db_session.add(conversation)
            await self.db_session.commit()
            await self.db_session.refresh(conversation)
            return conversation
        except SQLAlchemyError:
            await self.db_session.rollback()
            return None

    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """
        Retrieve a conversation by its unique ID.

        Parameters
        ----------
        conversation_id : str
            The unique identifier of the conversation.

        Returns
        -------
        Optional[Conversation]
            The Conversation object if found, otherwise None.
        """
        try:
            result = await self.db_session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            return None

    async def get_by_user_id(
            self,
            user_id: str,
            active_only: bool = False,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            sort_by: str = "updated_at",
            sort_dir: str = "desc"
    ) -> List[Conversation]:
        """
        Retrieve conversations for a specific user with optional filtering, pagination, and sorting.

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
            A list of Conversation objects for the user, ordered and paginated.

        Raises
        ------
        ValueError
            If user_id is empty or invalid sort direction is provided.
        """
        if not user_id:
            raise ValueError("user_id must be a non-empty string.")

        if sort_dir not in {"asc", "desc"}:
            raise ValueError("sort_dir must be either 'asc' or 'desc'.")

        try:
            query = select(Conversation).where(Conversation.user_id == user_id)

            if active_only:
                query = query.where(Conversation.is_active.is_(True))

            sort_column = getattr(Conversation, sort_by, None)
            if sort_column is None:
                raise ValueError(f"Invalid sort_by field: {sort_by}")

            if sort_dir == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)

            result = await self.db_session.execute(query)
            conversations = list(result.scalars().all())

            # logger.info(f"Retrieved {len(conversations)} conversations for user_id={user_id}")
            return conversations

        except Exception as e:
            logger.error(f"Error retrieving conversations for user_id={user_id}: {e}")
            raise

    async def update(self, conversation: Conversation) -> Optional[Conversation]:
        """
        Update an existing conversation in the database.

        Parameters
        ----------
        conversation : Conversation
            The Conversation object with updated fields.

        Returns
        -------
        Optional[Conversation]
            The updated Conversation object or None if update failed.
        """
        try:
            await self.db_session.commit()
            await self.db_session.refresh(conversation)
            return conversation
        except SQLAlchemyError:
            await self.db_session.rollback()
            return None

    async def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation by its unique ID.

        Parameters
        ----------
        conversation_id : str
            The unique identifier of the conversation to be deleted.

        Returns
        -------
        bool
            True if the conversation was successfully deleted, False otherwise.
        """
        try:
            conversation = await self.get_by_id(conversation_id)
            if conversation:
                await self.db_session.delete(conversation)
                await self.db_session.commit()
                return True
            return False
        except SQLAlchemyError:
            await self.db_session.rollback()
            return False
