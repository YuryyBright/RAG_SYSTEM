# app/adapters/auth/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

import jwt
from app.core.interfaces.auth import AuthInterface
from app.core.entities.user import User
from app.utils.security import verify_password, get_password_hash
from app.utils.logger_util import get_logger
from app.config import settings

# Configure logger
logger = get_logger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class JWTAuth(AuthInterface):
    """
    JWT implementation of the authentication interface.

    This class provides JWT-based authentication and authorization functionality.

    Attributes:
        secret_key (str): The secret key used for JWT encoding and decoding.
        algorithm (str): The algorithm used for JWT encoding and decoding.
        access_token_expire_minutes (int): The expiration time for access tokens in minutes.
    """

    def __init__(
            self,
            secret_key: str = None,
            algorithm: str = "HS256",
            access_token_expire_minutes: int = 30
    ):
        """
        Initialize the JWT authentication service.

        Args:
            secret_key (str): The secret key used for JWT encoding and decoding.
                             If None, it will be read from the environment.
            algorithm (str): The algorithm used for JWT encoding and decoding.
            access_token_expire_minutes (int): The expiration time for access tokens in minutes.
        """
        self.secret_key = secret_key or settings.JWT_SECRET_KEY
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    async def authenticate_user(
            self,
            username: str,
            password: str,
            user_provider: Callable
    ) -> Optional[User]:
        """
        Authenticate a user by username and password.

        Args:
            username (str): The username of the user.
            password (str): The password of the user.
            user_provider (Callable): A provider function that returns a user by username.

        Returns:
            Optional[User]: The authenticated user, or None if authentication failed.
        """
        user = await user_provider(username)
        if not user:
            logger.info(f"Authentication failed: User {username} not found")
            return None

        if not verify_password(password, user.hashed_password):
            logger.info(f"Authentication failed: Invalid password for user {username}")
            return None

        logger.info(f"User {username} authenticated successfully")
        return user

    def create_access_token(
            self,
            data: Dict[str, Any],
            expires_delta: Optional[timedelta] = None
    ) -> tuple[str, datetime]:
        """
        Create an access token.

        Args:
            data (Dict[str, Any]): The data to encode in the token.
            expires_delta (Optional[timedelta]): The expiration time for the token.
                                                If None, the default expiration time is used.

        Returns:
            tuple[str, datetime]: The encoded JWT token and expiration datetime.
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt, expire

    def get_password_hash(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Parameters
        ----------
        password : str
            The plaintext password to be hashed.

        Returns
        -------
        str
            The hashed password, which can be stored securely in a database.
        """
        return get_password_hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hashed value.

        Parameters
        ----------
        plain_password : str
            The plaintext password provided by the user.
        hashed_password : str
            The hashed password stored in the database.

        Returns
        -------
        bool
            True if the plaintext password matches the hashed password, False otherwise.
        """
        return verify_password(plain_password, hashed_password)
    async def get_current_user(
            self,
            token: str,
            user_provider: Callable
    ) -> User:
        """
        Get the current user from a token.

        Args:
            token (str): The JWT token.
            user_provider (Callable): A provider function that returns a user by username.

        Returns:
            User: The current user.

        Raises:
            HTTPException: If the token is invalid or the user is not found.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except jwt.PyJWTError as e:
            logger.warning(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_provider(username)
        if user is None:
            logger.warning(f"User from token not found: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    async def get_current_active_user(
            self,
            token: str = Depends(oauth2_scheme),
            user_provider: Callable = None
    ) -> User:
        """
        Get the current active user.

        Args:
            token (str): The JWT token.
            user_provider (Callable): A provider function that returns a user by username.

        Returns:
            User: The current active user.

        Raises:
            HTTPException: If the user is inactive.
        """
        current_user = await self.get_current_user(token, user_provider)

        if not current_user.is_active:
            logger.warning(f"Inactive user attempt: {current_user.username}")
            raise HTTPException(status_code=400, detail="Inactive user")

        return current_user