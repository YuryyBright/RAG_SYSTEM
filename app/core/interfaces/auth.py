# core/interfaces/auth.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AuthInterface(ABC):
    """
    Interface for authentication and authorization services.

    This abstract class defines the methods that any authentication
    implementation must provide to work with the system.
    """

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            plain_password (str): The password in plain text.
            hashed_password (str): The hashed password.

        Returns:
            bool: True if the password matches the hash, False otherwise.
        """
        pass

    @abstractmethod
    def get_password_hash(self, password: str) -> str:
        """
        Get the hash of a password.

        Args:
            password (str): The password in plain text.

        Returns:
            str: The hashed password.
        """
        pass

    @abstractmethod
    async def authenticate_user(self, username: str, password: str, user_provider: Any) -> Optional[Any]:
        """
        Authenticate a user by username and password.

        Args:
            username (str): The username of the user.
            password (str): The password of the user.
            user_provider (Any): A provider function that returns a user by username.

        Returns:
            Optional[Any]: The authenticated user, or None if authentication failed.
        """
        pass

    @abstractmethod
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[Any] = None) -> str:
        """
        Create an access token.

        Args:
            data (Dict[str, Any]): The data to encode in the token.
            expires_delta (Optional[Any]): The expiration time for the token.
                                         If None, the default expiration time is used.

        Returns:
            str: The encoded token.
        """
        pass

    @abstractmethod
    async def get_current_user(self, token: str, user_provider: Any) -> Any:
        """
        Get the current user from a token.

        Args:
            token (str): The token.
            user_provider (Any): A provider function that returns a user by username.

        Returns:
            Any: The current user.

        Raises:
            Exception: If the token is invalid or the user is not found.
        """
        pass