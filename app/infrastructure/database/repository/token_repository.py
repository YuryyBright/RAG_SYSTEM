# app/infrastructure/database/repository/token_repository.py
import hmac

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

    async def store_token(self, user_id: str, token: str, expires_at: datetime):
        """
        Store an access token in the database.

        Parameters
        ----------
        user_id : str
            ID of the user.
        token : str
            JWT token string.
        expires_at : datetime
            Expiration time of the token.

        Returns
        -------
        Token
            The created token object.
        """
        return await self.create_token(token=token, user_id=user_id, expires_at=expires_at)

    async def revoke_token(self, user_id: str, token: str) -> bool:
        """
        Revoke a token, marking it as unusable.

        Parameters
        ----------
        user_id : str
            The ID of the user associated with the token.
        token : str
            The token string to revoke.

        Returns
        -------
        bool
            True if the token was revoked, False otherwise.
        """
        try:
            db_token = await self.get_token(token, user_id)
            if db_token:
                db_token.is_revoked = True
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            await self.db.rollback()
            return False

    async def is_token_revoked(self, user_id: str, token: str) -> bool:
        """
        Check if a token is revoked.

        Parameters
        ----------
        user_id : str
            The ID of the user associated with the token.
        token : str
            The token string to check.

        Returns
        -------
        bool
            True if the token is revoked, False otherwise.
        """
        try:
            db_token = await self.get_token(token, user_id)
            return db_token and getattr(db_token, 'is_revoked', False)
        except Exception as e:
            logger.error(f"Error checking if token is revoked: {e}")
            return False

    async def store_reset_token(self, user_id: str, token: str, expires_at: datetime):
        """
        Store a password reset token in the database.

        Parameters
        ----------
        user_id : str
            ID of the user.
        token : str
            Reset token string.
        expires_at : datetime
            Expiration time of the token.

        Returns
        -------
        Token
            The created token object.
        """
        try:
            db_token = Token(
                id=str(uuid4()),
                token=token,
                user_id=user_id,
                expires_at=expires_at,
                token_type="reset"
            )
            self.db.add(db_token)
            await self.db.commit()
            return db_token
        except Exception as e:
            logger.error(f"Error storing reset token: {e}")
            await self.db.rollback()
            return None

    async def is_reset_token_valid(self, user_id: str, token: str) -> bool:
        """
        Check if a reset token is valid.

        Parameters
        ----------
        user_id : str
            The ID of the user associated with the token.
        token : str
            The reset token string to check.

        Returns
        -------
        bool
            True if the token is valid, False otherwise.
        """
        try:
            result = await self.db.execute(
                select(Token).where(
                    and_(
                        Token.token == token,
                        Token.user_id == user_id,
                        Token.token_type == "reset",
                        Token.expires_at > datetime.utcnow(),
                        Token.is_revoked.is_(False)
                    )
                )
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking reset token validity: {e}")
            return False

    async def invalidate_reset_token(self, user_id: str, token: str) -> bool:
        """
        Invalidate a reset token.

        Parameters
        ----------
        user_id : str
            The ID of the user associated with the token.
        token : str
            The reset token string to invalidate.

        Returns
        -------
        bool
            True if the token was invalidated, False otherwise.
        """
        try:
            result = await self.db.execute(
                select(Token).where(
                    and_(
                        Token.token == token,
                        Token.user_id == user_id,
                    )
                )
            )
            token_obj = result.scalar_one_or_none()
            if token_obj:
                token_obj.is_revoked = True
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error invalidating reset token: {e}")
            await self.db.rollback()
            return False