# app/adapters/auth/service.py
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User
from app.infrastructure.database.repository.user_repository import UserRepository
from app.infrastructure.database.repository.token_repository import TokenRepository
from app.adapters.auth.security import JWTAuth
from app.utils.logger_util import get_logger
from app.utils.security import generate_session_id, generate_csrf_token
from app.config import settings
from infrastructure.database.repository.session_repository import SessionRepository
from fastapi import Request
# Configure logger
logger = get_logger(__name__)


class AuthService:
    """
    Service class for handling authentication and user-related operations.

    This class orchestrates user authentication, registration, and token management
    by coordinating between repositories and the auth provider.

    Attributes
    ----------
    user_repo : UserRepository
        Repository for user-related database operations.
    token_repo : TokenRepository
        Repository for token-related database operations.
    session_repo : SessionRepository
        Repository for session-related database operations.
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
        self.session_repo = SessionRepository(db)
        self.jwt_auth = JWTAuth()
        self.db = db

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
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

        async def user_provider(username_or_email: str) -> Optional[User]:
            # Determine if username is actually an email
            if '@' in username_or_email:
                return await self.user_repo.get_by_email(username_or_email)
            else:
                return await self.user_repo.get_by_username(username_or_email)

        return await self.jwt_auth.authenticate_user(username, password, user_provider)

    async def register_user(self, username: str, email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
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
            hashed_password = self.jwt_auth.get_password_hash(password)
            user = await self.user_repo.create_user(username, email, hashed_password)
            logger.info(f"User registered successfully: {username}")
            return user, None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error during user registration: {e}")
            return None, "Error registering user"

    async def verify_session(self, session_id: str, csrf_token: Optional[str]) -> Optional[User]:
        """
        Verify session ID and CSRF token, and return the user if valid.

        Parameters
        ----------
        session_id : str
            The session ID from the cookie.
        csrf_token : Optional[str]
            The CSRF token from the header.

        Returns
        -------
        Optional[User]
            The associated user if the session and CSRF token are valid, otherwise None.

        Raises
        ------
        HTTPException
            If CSRF token is invalid or session is expired/invalid.
        """
        session = await self.validate_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        if not csrf_token or not await self.verify_csrf_token(session_id, csrf_token):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")

        user_id = session.get("user_id")
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    async def create_user_token(self, user_id: str, username: str) -> Tuple[Optional[str], Optional[datetime]]:
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
        Tuple[str or None, datetime or None]
            The access token and its expiration datetime, or None if error.
        """
        try:
            access_token, expire = self.jwt_auth.create_access_token(
                data={"sub": user_id, "username": username}
            )

            # Store token in database for potential revocation
            await self.token_repo.store_token(user_id, access_token, expire)

            logger.info(f"Access token created for user: {username}")
            return access_token, expire
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            return None, None

    async def verify_token(self, token: str) -> Optional[User]:
        """
        Verify the validity of an access token and retrieve the associated user.

        Parameters
        ----------
        token : str
            The access token to verify.

        Returns
        -------
        Optional[User]
            The user associated with the token if valid, otherwise None.

        Raises
        ------
        Exception
            If an error occurs during token verification or user retrieval.
        """
        return await self.get_user_by_token(token)


    async def logout_user(self, user_id: str, token: str) -> bool:
        """
        Invalidate a user's access token.

        Parameters
        ----------
        user_id : str
            The ID of the user.
        token : str
            The access token to invalidate.

        Returns
        -------
        bool
            True if the token was successfully invalidated, False otherwise.
        """
        try:
            # Revoke the token in the database
            success = await self.token_repo.revoke_token(user_id, token)

            if success:
                logger.info(f"Token successfully revoked for user: {user_id}")
            else:
                logger.warning(f"Token revocation failed for user: {user_id}")

            return success
        except Exception as e:
            logger.error(f"Error during token revocation: {e}")
            return False

    async def create_user_session(
            self,
            user_id: str,
            username: str,
            remember: bool = False,
            request: Optional[Request] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[datetime]]:
        """
        Create a new session for cookie-based authentication.

        Parameters
        ----------
        user_id : str
            The ID of the user.
        username : str
            The username of the user.
        remember : bool, optional
            Whether to create a long-lived session. Default is False.
        request : Request, optional
            The current request to extract user-agent and IP.

        Returns
        -------
        Tuple[str or None, str or None, datetime or None]
            The session ID, CSRF token, and expiration datetime, or None if error.
        """
        try:
            # Generate session ID
            session_id = generate_session_id()

            # Generate CSRF token
            csrf_token = generate_csrf_token(session_id)

            # Set expiration based on remember flag
            if remember:
                expire = datetime.utcnow() + timedelta(days=30)
            else:
                expire = datetime.utcnow() + timedelta(hours=24)

            # Extract device/IP info from request
            user_agent = request.headers.get("user-agent") if request else None
            ip_address = request.client.host if request else None

            # Store session
            success = await self.session_repo.create_session(
                session_id=session_id,
                user_id=user_id,
                username=username,
                expires_at=expire,
                csrf_token=csrf_token,
                remember=remember,
                user_agent=user_agent,
                ip_address=ip_address
            )

            if not success:
                logger.warning(f"Failed to create session for user: {user_id}")
                return None, None, None

            logger.info(f"Session created for user: {username}")
            return session_id, csrf_token, expire
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None, None, None

    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session from a cookie.

        Parameters
        ----------
        session_id : str
            The session ID from the cookie.

        Returns
        -------
        Dict[str, Any] or None
            The session data if valid, otherwise None.
        """
        try:
            # Retrieve session from database
            session = await self.session_repo.get_session(session_id)

            if not session:
                logger.warning(f"Session not found: {session_id[:8]}...")
                return None

            # Check if session is expired
            if session.get("expires_at") < datetime.utcnow():
                logger.warning(f"Session expired: {session_id[:8]}...")
                await self.session_repo.delete_session(session_id)
                return None

            return session
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None

    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.

        Parameters
        ----------
        session_id : str
            The session ID to invalidate.

        Returns
        -------
        bool
            True if the session was successfully invalidated, False otherwise.
        """
        try:
            success = await self.session_repo.delete_session(session_id)

            if success:
                logger.info(f"Session successfully invalidated: {session_id[:8]}...")
            else:
                logger.warning(f"Session invalidation failed: {session_id[:8]}...")

            return success
        except Exception as e:
            logger.error(f"Error during session invalidation: {e}")
            return False

    async def refresh_session(self, session_id: str) -> Tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[datetime]]:
        """
        Refresh a session with a new ID and CSRF token.

        Parameters
        ----------
        session_id : str
            The current session ID.

        Returns
        -------
        Tuple[str or None, str or None, str or None, str or None, datetime or None]
            user_id, username, new_session_id, csrf_token, expiration if successful, otherwise None.
        """
        try:
            # Validate current session
            session = await self.validate_session(session_id)

            if not session:
                return None, None, None, None, None

            # Extract session data
            user_id = session.get("user_id")
            username = session.get("username")
            remember = session.get("remember", False)

            # Invalidate the old session
            await self.invalidate_session(session_id)

            # Create a new session
            new_session_id, csrf_token, expire = await self.create_user_session(
                user_id, username, remember
            )

            if not new_session_id:
                logger.warning(f"Failed to refresh session for user: {username}")
                return None, None, None, None, None

            logger.info(f"Session refreshed for user: {username}")
            return user_id, username, new_session_id, csrf_token, expire
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return None, None, None, None, None

    async def get_user_by_token(self, token: str) -> Optional[User]:
        """
        Get a user by their access token.

        Parameters
        ----------
        token : str
            The access token.

        Returns
        -------
        User or None
            The user if the token is valid, otherwise None.
        """
        try:
            # Decode token
            payload = self.jwt_auth.decode_access_token(token)

            if not payload:
                logger.warning(f"Invalid token: {token[:8]}...")
                return None

            user_id = payload.get("sub")
            if not user_id:
                logger.warning(f"No user ID in token: {token[:8]}...")
                return None

            # Check if token is revoked
            is_revoked = await self.token_repo.is_token_revoked(user_id, token)

            if is_revoked:
                logger.warning(f"Token is revoked: {token[:8]}...")
                return None

            # Get user from database
            user = await self.user_repo.get_by_id(user_id)

            if not user:
                logger.warning(f"User not found for token: {token[:8]}...")
                return None

            return user
        except Exception as e:
            logger.error(f"Error retrieving user by token: {e}")
            return None

    async def get_user_by_session_id(self, session_id: str) -> Optional[User]:
        """
        Get a user by their session ID.

        Parameters
        ----------
        session_id : str
            The session ID.

        Returns
        -------
        User or None
            The user if the session is valid, otherwise None.
        """
        try:
            # Validate session
            session = await self.validate_session(session_id)

            if not session:
                return None

            user_id = session.get("user_id")

            # Get user from database
            user = await self.user_repo.get_by_id(user_id)

            if not user:
                logger.warning(f"User not found for session: {session_id[:8]}...")
                await self.session_repo.delete_session(session_id)
                return None

            return user
        except Exception as e:
            logger.error(f"Error retrieving user by session: {e}")
            return None

    async def verify_csrf_token(self, session_id: str, csrf_token: str) -> bool:
        """
        Verify that a CSRF token is valid for a session.

        Parameters
        ----------
        session_id : str
            The session ID.
        csrf_token : str
            The CSRF token to verify.

        Returns
        -------
        bool
            True if the CSRF token is valid, False otherwise.
        """
        try:
            # Get session from database
            session = await self.session_repo.get_session(session_id)

            if not session:
                logger.warning(f"Session not found for CSRF verification: {session_id[:8]}...")
                return False

            # Get stored CSRF token
            stored_csrf_token = session.get("csrf_token")

            if not stored_csrf_token:
                logger.warning(f"No CSRF token in session: {session_id[:8]}...")
                return False

            # Check if tokens match
            from app.utils.security import is_valid_csrf_token
            is_valid = is_valid_csrf_token(csrf_token, session_id)

            if not is_valid:
                logger.warning(f"Invalid CSRF token for session: {session_id[:8]}...")

            return is_valid
        except Exception as e:
            logger.error(f"Error verifying CSRF token: {e}")
            return False

    async def request_password_reset(self, email: str) -> bool:
        """
        Request a password reset for a user.

        Parameters
        ----------
        email : str
            The email address of the user.

        Returns
        -------
        bool
            True if the reset request was successful, False otherwise.
        """
        try:
            # Check if user exists
            user = await self.user_repo.get_by_email(email)

            if not user:
                logger.info(f"Password reset requested for non-existent email: {email}")
                return False

            # Generate reset token
            reset_token, expire = self.jwt_auth.create_access_token(
                data={"sub": user.id, "purpose": "password_reset"},
                expires_delta=timedelta(hours=1)  # Short-lived token for security
            )

            # Store reset token in database
            await self.token_repo.store_reset_token(user.id, reset_token, expire)

            # TODO: Send reset email with token
            # This would typically call an email service

            logger.info(f"Password reset requested for user: {user.username}")
            return True
        except Exception as e:
            logger.error(f"Error during password reset request: {e}")
            return False

    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset a user's password using a reset token.

        Parameters
        ----------
        token : str
            The password reset token.
        new_password : str
            The new password.

        Returns
        -------
        bool
            True if the password was successfully reset, False otherwise.
        """
        try:
            # Decode token
            payload = self.jwt_auth.decode_access_token(token)

            if not payload:
                logger.warning(f"Invalid reset token: {token[:8]}...")
                return False

            # Verify token purpose
            if payload.get("purpose") != "password_reset":
                logger.warning(f"Token has wrong purpose: {token[:8]}...")
                return False

            user_id = payload.get("sub")

            if not user_id:
                logger.warning(f"No user ID in reset token: {token[:8]}...")
                return False

            # Check if token is valid in database
            is_valid = await self.token_repo.is_reset_token_valid(user_id, token)

            if not is_valid:
                logger.warning(f"Reset token is not valid: {token[:8]}...")
                return False

            # Hash new password
            hashed_password = self.jwt_auth.get_password_hash(new_password)

            # Update password
            success = await self.user_repo.update_password(user_id, hashed_password)

            if not success:
                logger.warning(f"Failed to update password for user: {user_id}")
                return False

            # Invalidate reset token
            await self.token_repo.invalidate_reset_token(user_id, token)

            # Invalidate all sessions for this user
            await self.session_repo.delete_user_sessions(user_id)

            logger.info(f"Password reset successful for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error during password reset: {e}")
            return False

    async def validate_session_without_csrf(self, session_id: str) -> Optional[User]:
        """
        Validate a session without CSRF verification (for GET requests).
        """
        session = await self.validate_session(session_id)
        if not session:
            return None

        user_id = session.get("user_id")
        return await self.user_repo.get_by_id(user_id)