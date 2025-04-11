# app/core/interfaces/auth.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime, timedelta

from app.core.entities.user import User


class AuthInterface(ABC):
    """
    Interface for authentication services.

    Defines the contract for authentication implementations.
    """

    @abstractmethod
    async def authenticate_user(
            self,
            username: str,
            password: str,
            user_provider: Callable
    ) -> Optional[User]:
        """
        Authenticate a user by username and password.

        Args:
            username: The username of the user.
            password: The password of the user.
            user_provider: A provider function that returns a user by username.

        Returns:
            Optional[User]: The authenticated user, or None if authentication failed.
        """
        pass

    @abstractmethod
    def create_access_token(
            self,
            data: Dict[str, Any],
            expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, datetime]:
        """
        Create an access token.

        Args:
            data: The data to encode in the token.
            expires_delta: The expiration time for the token.

        Returns:
            Tuple[str, datetime]: The encoded JWT token and expiration datetime.
        """
        pass

    @abstractmethod
    async def get_current_user(
            self,
            token: str,
            user_provider: Callable
    ) -> User:
        """
        Get the current user from a token.

        Args:
            token: The JWT token.
            user_provider: A provider function that returns a user by username.

        Returns:
            User: The current user.

        Raises:
            HTTPException: If the token is invalid or the user is not found.
        """
        pass

    @abstractmethod
    async def get_current_active_user(
            self,
            token: str,
            user_provider: Callable
    ) -> User:
        """
        Get the current active user.

        Args:
            token: The JWT token.
            user_provider: A provider function that returns a user by username.

        Returns:
            User: The current active user.

        Raises:
            HTTPException: If the user is inactive.
        """
        pass

    @abstractmethod
    def verify_token(
            self,
            token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify a token.

        Args:
            token: The JWT token.

        Returns:
            Optional[Dict[str, Any]]: The decoded token payload if valid, None otherwise.
        """
        pass