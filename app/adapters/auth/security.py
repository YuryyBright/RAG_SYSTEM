# app/adapters/auth/security.py
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from core.interfaces.auth import AuthInterface
from core.entities.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "supercecretkey123")
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            plain_password (str): The password in plain text.
            hashed_password (str): The hashed password.

        Returns:
            bool: True if the password matches the hash, False otherwise.
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Get the hash of a password.

        Args:
            password (str): The password in plain text.

        Returns:
            str: The hashed password.
        """
        return pwd_context.hash(password)

    async def authenticate_user(
            self,
            username: str,
            password: str,
            user_provider: Any
    ) -> Optional[User]:
        """
        Authenticate a user by username and password.

        Args:
            username (str): The username of the user.
            password (str): The password of the user.
            user_provider (Any): A provider function that returns a user by username.

        Returns:
            Optional[User]: The authenticated user, or None if authentication failed.
        """
        user = await user_provider(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(
            self,
            data: Dict[str, Any],
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create an access token.

        Args:
            data (Dict[str, Any]): The data to encode in the token.
            expires_delta (Optional[timedelta]): The expiration time for the token.
                                                If None, the default expiration time is used.

        Returns:
            str: The encoded JWT token.
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    async def get_current_user(
            self,
            token: str,
            user_provider: Any
    ) -> User:
        """
        Get the current user from a token.

        Args:
            token (str): The JWT token.
            user_provider (Any): A provider function that returns a user by username.

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
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_provider(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    async def get_current_active_user(
            self,
            current_user: User = Depends(oauth2_scheme)
    ) -> User:
        """
        Get the current active user.

        Args:
            current_user (User): The current user, obtained from the token.

        Returns:
            User: The current active user.

        Raises:
            HTTPException: If the user is inactive.
        """
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user