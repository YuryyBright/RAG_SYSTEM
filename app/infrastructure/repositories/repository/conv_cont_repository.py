from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.infrastructure.database.db_models import ConversationContext

class ConversationContextRepository:
    """
    Repository for managing ConversationContext entities in the database.

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

    async def create(self, context: ConversationContext) -> Optional[ConversationContext]:
        """
        Create a new conversation context in the database.

        Parameters
        ----------
        context : ConversationContext
            The ConversationContext object to be added to the database.

        Returns
        -------
        Optional[ConversationContext]
            The newly created ConversationContext object with updated fields, or None if failed.
        """
        try:
            self.db_session.add(context)
            await self.db_session.commit()
            await self.db_session.refresh(context)
            return context
        except SQLAlchemyError:
            await self.db_session.rollback()
            return None

    async def get_by_id(self, context_id: str) -> Optional[ConversationContext]:
        """
        Retrieve a conversation context by its unique ID.

        Parameters
        ----------
        context_id : str
            The unique identifier of the conversation context.

        Returns
        -------
        Optional[ConversationContext]
            The ConversationContext object if found, otherwise None.
        """
        try:
            result = await self.db_session.execute(
                select(ConversationContext).where(ConversationContext.id == context_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            return None

    async def get_by_conversation_id(self, conversation_id: str,
                                     context_type: Optional[str] = None,
                                     limit: Optional[int] = None,
                                     order_by_priority: bool = True) -> List[ConversationContext]:
        """
        Retrieve all conversation contexts for a specific conversation.

        Parameters
        ----------
        conversation_id : str
            The unique identifier of the conversation.
        context_type : Optional[str], optional
            Filter by context type if provided.
        limit : Optional[int], optional
            Limit the number of returned results.
        order_by_priority : bool, optional
            If True, order by priority and updated_at, else only by updated_at (default is True).

        Returns
        -------
        List[ConversationContext]
            A list of ConversationContext objects for the conversation.
        """
        try:
            query = select(ConversationContext).where(ConversationContext.conversation_id == conversation_id)
            if context_type:
                query = query.where(ConversationContext.context_type == context_type)

            if order_by_priority:
                query = query.order_by(ConversationContext.priority.desc(), ConversationContext.updated_at.desc())
            else:
                query = query.order_by(ConversationContext.updated_at.desc())

            if limit:
                query = query.limit(limit)

            result = await self.db_session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError:
            return []

    async def update(self, context: ConversationContext) -> Optional[ConversationContext]:
        """
        Update an existing conversation context in the database.

        Parameters
        ----------
        context : ConversationContext
            The ConversationContext object with updated fields.

        Returns
        -------
        Optional[ConversationContext]
            The updated ConversationContext object or None if update failed.
        """
        try:
            await self.db_session.commit()
            await self.db_session.refresh(context)
            return context
        except SQLAlchemyError:
            await self.db_session.rollback()
            return None

    async def delete(self, context_id: str) -> bool:
        """
        Delete a conversation context by its unique ID.

        Parameters
        ----------
        context_id : str
            The unique identifier of the conversation context to be deleted.

        Returns
        -------
        bool
            True if the conversation context was successfully deleted, False otherwise.
        """
        try:
            context = await self.get_by_id(context_id)
            if context:
                await self.db_session.delete(context)
                await self.db_session.commit()
                return True
            return False
        except SQLAlchemyError:
            await self.db_session.rollback()
            return False

    async def semantic_search(self, conversation_id: str, query_embedding, limit: int = 5):
        """
        Perform semantic search on context embeddings for a conversation.

        This is a placeholder - actual implementation will depend on your database's
        vector similarity search capabilities.

        Parameters
        ----------
        conversation_id : str
            The unique identifier of the conversation.
        query_embedding : Any
            The embedding vector to compare against.
        limit : int, optional
            Limit the number of returned results (default is 5).
        """
        pass
