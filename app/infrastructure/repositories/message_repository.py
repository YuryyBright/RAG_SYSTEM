from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.infrastructure.database.db_models import Message

class MessageRepository:
    """
    Repository for managing Message entities in the database.

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

    async def create(self, message: Message) -> Message:
        """
        Create a new message in the database.

        Parameters
        ----------
        message : Message
            The Message object to be added to the database.

        Returns
        -------
        Message
            The newly created Message object with updated fields.
        """
        self.db_session.add(message)
        await self.db_session.commit()
        await self.db_session.refresh(message)
        return message

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """
        Retrieve a message by its unique ID.

        Parameters
        ----------
        message_id : str
            The unique identifier of the message.

        Returns
        -------
        Optional[Message]
            The Message object if found, otherwise None.
        """
        result = await self.db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_by_conversation_id(self, conversation_id: str,
                                     include_hidden: bool = False,
                                     limit: int | None = None,
                                     offset: int | None = None,
                                     ) -> List[Message]:
        """
        Retrieve all messages for a specific conversation.

        Parameters
        ----------
        conversation_id : str
            The unique identifier of the conversation.
        include_hidden : bool, optional
            If False, hidden messages will be excluded (default is False).
        limit : int, optional
            Limit the number of messages to return.
        offset : int, optional
            If specified, only messages starting from `offset` will be returned.

        Returns
        -------
        List[Message]
            A list of Message objects for the conversation, ordered by creation time.
        """
        stmt = select(Message).where(Message.conversation_id == conversation_id)
        if not include_hidden:
            stmt = stmt.where(Message.is_hidden.is_(False))
        stmt = stmt.order_by(Message.created_at)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def update(self, message: Message) -> Message:
        """
        Update an existing message in the database.

        Parameters
        ----------
        message : Message
            The Message object with updated fields.

        Returns
        -------
        Message
            The updated Message object.
        """
        await self.db_session.commit()
        await self.db_session.refresh(message)
        return message

    async def delete(self, message_id: str) -> bool:
        """
        Delete a message by its unique ID.

        Parameters
        ----------
        message_id : str
            The unique identifier of the message to be deleted.

        Returns
        -------
        bool
            True if the message was successfully deleted, False otherwise.
        """
        message = await self.get_by_id(message_id)
        if message:
            await self.db_session.delete(message)
            await self.db_session.commit()
            return True
        return False