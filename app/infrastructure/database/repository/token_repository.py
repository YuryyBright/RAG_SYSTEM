# app/infrastructure/database/repository/token_repository.py
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import uuid4

from app.infrastructure.database.db_models import Token
from app.utils.logger_util import get_logger

logger = get_logger(__name__)

class TokenRepository:
    """
    Repository class for managing token-related database operations.

    Attributes
    ----------
    db : AsyncSession
        The database session used for executing queries.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the TokenRepository with a database session.

        Parameters
        ----------
        db : AsyncSession
            The database session to use for queries.
        """
        self.db = db

    async def create_token(self, token: str, user_id: str, expires_at: datetime):
        """
        Create a new token in the database.

        Parameters
        ----------
        token : str
            The token string.
        user_id : str
            The ID of the user associated with the token.
        expires_at : datetime
            The expiration date and time of the token.

        Returns
        -------
        Token
            The created token object.
        """
        db_token = Token(
            id=str(uuid4()),
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        self.db.add(db_token)
        await self.db.commit()
        return db_token

    async def get_token(self, token: str, user_id: str):
        """
        Retrieve a token by its value and associated user ID.

        Parameters
        ----------
        token : str
            The token string to retrieve.
        user_id : str
            The ID of the user associated with the token.

        Returns
        -------
        Token or None
            The token object if found, otherwise None.
        """
        result = await self.db.execute(
            select(Token).where(
                and_(Token.token == token, Token.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def delete_token(self, token: str, user_id: str):
        """
        Delete a token by its value and associated user ID.

        Parameters
        ----------
        token : str
            The token string to delete.
        user_id : str
            The ID of the user associated with the token.

        Returns
        -------
        bool
            True if the token was deleted, False otherwise.
        """
        db_token = await self.get_token(token, user_id)
        if db_token:
            await self.db.delete(db_token)
            await self.db.commit()
            return True
        return False