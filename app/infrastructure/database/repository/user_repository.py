# app/infrastructure/database/repository/user_repository.py
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from starlette import status

from app.infrastructure.database.db_models import User, Token
from app.utils.security import get_password_hash, verify_password
from app.utils.logger_util import get_logger

logger = get_logger(__name__)

class UserRepository:
    """
    Repository class for managing user-related database operations.

    Attributes
    ----------
    db : AsyncSession
        The database session used for executing queries.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the UserRepository with a database session.

        Parameters
        ----------
        db : AsyncSession
            The database session to use for queries.
        """
        self.db = db

    async def get_by_username(self, username: str):
        """
        Retrieve a user by their username.

        Parameters
        ----------
        username : str
            The username of the user to retrieve.

        Returns
        -------
        User or None
            The user object if found, otherwise None.
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def update_user_profile(self, user: User, name: str, email: str, timezone: str, theme: str):
        """
        Update a user's profile fields.

        Parameters
        ----------
        user : User
            The user instance to update.
        name : str
            The new full name.
        email : str
            The new email address.
        timezone : str
            The new timezone string.
        theme : str
            The new theme preference.

        Raises
        ------
        HTTPException
            If the email is already registered to another user.
        """
        # Check if the new email is already used by another user
        result = await self.db.execute(select(User).where(User.email == email, User.id != user.id))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        # Apply updates
        user.name = name
        user.email = email
        user.timezone = timezone
        user.theme = theme

        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"User profile updated: {user.id}")
    async def get_by_email(self, email: str):
        """
        Retrieve a user by their email.

        Parameters
        ----------
        email : str
            The email of the user to retrieve.

        Returns
        -------
        User or None
            The user object if found, otherwise None.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str):
        """
        Retrieve a user by their ID.

        Parameters
        ----------
        user_id : str
            The ID of the user to retrieve.

        Returns
        -------
        User or None
            The user object if found, otherwise None.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def username_exists(self, username: str) -> bool:
        """
        Check if a username already exists in the database.

        Parameters
        ----------
        username : str
            The username to check.

        Returns
        -------
        bool
            True if the username exists, False otherwise.
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none() is not None

    async def email_exists(self, email: str) -> bool:
        """
        Check if an email already exists in the database.

        Parameters
        ----------
        email : str
            The email to check.

        Returns
        -------
        bool
            True if the email exists, False otherwise.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none() is not None

    async def create_user(self, username: str, email: str, password: str):
        """
        Create a new user in the database.

        Parameters
        ----------
        username : str
            The username of the new user.
        email : str
            The email of the new user.
        password : str
            The plaintext password of the new user.

        Returns
        -------
        User
            The created user object.
        """
        hashed_password = get_password_hash(password)
        user = User(
            id=str(uuid4()),
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # Add to UserRepository
    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """
        Update a user's password.

        Parameters
        ----------
        user_id : str
            The ID of the user.
        hashed_password : str
            The new hashed password.

        Returns
        -------
        bool
            True if the password was updated, False otherwise.
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(f"User not found for password update: {user_id}")
                return False

            user.hashed_password = hashed_password
            await self.db.commit()
            logger.info(f"Password updated for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            await self.db.rollback()
            return False

    async def delete_user(self, user: User) -> None:
        """
        Permanently delete a user from the database.

        Parameters
        ----------
        user : User
            The user object to delete.
        """
        await self.db.delete(user)
        await self.db.commit()
        logger.info(f"User deleted: {user.id}")

    async def deactivate_user(self, user: User) -> None:
        """
        Deactivate a user's account.

        Parameters
        ----------
        user : User
            The user object to deactivate.
        """
        user.is_active = False
        await self.db.commit()
        logger.info(f"User deactivated: {user.id}")

    async def reactivate_user(self, user: User) -> None:
        """
        Reactivate a user's account.

        Parameters
        ----------
        user : User
            The user object to reactivate.
        """
        user.is_active = True
        await self.db.commit()
        logger.info(f"User reactivated: {user.id}")

    async def update_avatar_url(self, user: User, avatar_url: str) -> None:
        """
        Update a user's avatar URL.

        Parameters
        ----------
        user : User
            The user object whose avatar URL is being updated.
        avatar_url : str
            The new avatar URL.
        """
        user.avatar_url = avatar_url
        await self.db.commit()
        logger.info(f"Avatar updated for user: {user.id}")