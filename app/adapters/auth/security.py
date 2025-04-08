# app/adapters/auth/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

import jwt
from app.core.interfaces.auth import AuthInterface
from app.core.entities.user import User
from app.infrastructure.database.repository.user_repository import UserRepository
from app.infrastructure.database.repository.token_repository import TokenRepository
from app.utils.security import verify_password, get_password_hash, create_access_token
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

    def get_password_hash(self, password: str) -> str:
        """
        Hash the password using bcrypt.

        Args:
            password (str): The plain password to hash.

        Returns:
            str: The hashed password.
        """
        return get_password_hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password using bcrypt.

        Args:
            plain_password (str): The plain password.
            hashed_password (str): The hashed password.

        Returns:
            bool: True if match, False otherwise.
        """
        return verify_password(plain_password, hashed_password)


class AuthService:
    """
    Service class for handling authentication and user-related operations.

    Attributes
    ----------
    user_repo : UserRepository
        Repository for user-related database operations.
    token_repo : TokenRepository
        Repository for token-related database operations.
    jwt_auth : JWTAuth
        Service for JWT-based authentication operations.
    db : AsyncSession
        The database session used for executing queries.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the AuthService with a database session.

        Parameters
        ----------
        db : AsyncSession
            The database session to use for queries.
        """
        self.user_repo = UserRepository(db)
        self.token_repo = TokenRepository(db)
        self.jwt_auth = JWTAuth()
        self.db = db

    async def authenticate_user(self, username: str, password: str):
        """
        Authenticate a user by username/email and password.

        Parameters
        ----------
        username : str
            The username or email of the user.
        password : str
            The plaintext password of the user.

        Returns
        -------
        User or None
            The authenticated user object if successful, otherwise None.
        """
        user = None
        # Determine if username is actually an email
        if '@' in username:
            user = await self.user_repo.get_by_email(username)
        else:
            user = await self.user_repo.get_by_username(username)

        if not user:
            logger.info(f"Authentication attempt for non-existent user: {username}")
            return None

        if not verify_password(password, user.hashed_password):
            logger.info(f"Failed login attempt for user: {username}")
            return None

        logger.info(f"User authenticated successfully: {username}")
        return user

    async def register_user(self, username: str, email: str, password: str):
        """
        Register a new user if the username and email don't already exist.

        Parameters
        ----------
        username : str
            The desired username for the new user.
        email : str
            The email address for the new user.
        password : str
            The plaintext password for the new user.

        Returns
        -------
        Tuple[User or None, str or None]
            The created user object and an error message (if any).
        """
        if await self.user_repo.username_exists(username):
            logger.warning(f"Registration attempt with existing username: {username}")
            return None, "Username already registered"

        if await self.user_repo.email_exists(email):
            logger.warning(f"Registration attempt with existing email: {email}")
            return None, "Email already registered"

        try:
            user = await self.user_repo.create_user(username, email, password)
            logger.info(f"User registered successfully: {username}")
            return user, None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error during user registration: {e}")
            return None, "Error registering user"

    async def create_user_token(self, user_id: str, username: str) -> Tuple[str, datetime]:
        """
        Create an access token for the user using the JWT auth service.

        Parameters
        ----------
        user_id : str
            The ID of the user.
        username : str
            The username of the user.

        Returns
        -------
        Tuple[str, datetime]
            The access token and its expiration datetime.
        """
        access_token, expire = self.jwt_auth.create_access_token(
            data={"sub": username},
            expires_delta=timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        )

        try:
            await self.token_repo.create_token(access_token, user_id, expire)
            logger.info(f"Access token created for user: {username}")
            return access_token, expire
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error storing token: {e}")
            return None, None

    async def logout_user(self, user_id: str, token: str) -> bool:
        """
        Invalidate a user's token.

        Parameters
        ----------
        user_id : str
            The ID of the user.
        token : str
            The token to invalidate.

        Returns
        -------
        bool
            True if the token was successfully invalidated, False otherwise.
        """
        try:
            result = await self.token_repo.delete_token(token, user_id)
            if result:
                logger.info(f"User logged out successfully: {user_id}")
                return True
            else:
                logger.warning(f"Logout attempt with invalid token for user: {user_id}")
                return False
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error during logout: {e}")
            return False

    async def verify_token(self, token: str) -> User:
        """
        Verify a token and return the associated user.

        Parameters
        ----------
        token : str
            The token to verify.

        Returns
        -------
        User
            The user associated with the token.

        Raises
        ------
        HTTPException
            If the token is invalid or the user is not found.
        """
        async def user_provider(username: str) -> User:
            return await self.user_repo.get_by_username(username)

        return await self.jwt_auth.get_current_user(token, user_provider)

    async def get_current_active_user(self, token: str) -> User:
        """
        Get the current active user from a token.

        Parameters
        ----------
        token : str
            The token to verify.

        Returns
        -------
        User
            The current active user.

        Raises
        ------
        HTTPException
            If the token is invalid, the user is not found, or the user is inactive.
        """
        async def user_provider(username: str) -> User:
            return await self.user_repo.get_by_username(username)

        return await self.jwt_auth.get_current_active_user(token, user_provider)

