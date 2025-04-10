# app/api/middleware_auth.py
from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, Union

from app.infrastructure.database.repository import get_async_db
from app.infrastructure.database.db_models import User
from app.adapters.auth.service import AuthService
from app.utils.logger_util import get_logger
from app.utils.security import COOKIE_NAME, CSRF_COOKIE_NAME

# Configure logger
logger = get_logger(__name__)

# Setup OAuth2 with token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


async def get_current_user(
        request: Request,
        token: Optional[str] = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_async_db)
) -> Optional[User]:
    """
    Get the current user from API token.

    Args:
        request: Request
        token: JWT token
        db: Database session

    Returns:
        User object if token is valid

    Raises:
        HTTPException: If token is invalid
    """
    auth_service = AuthService(db)

    try:
        if token:
            logger.info(f"Authentication check successful by token: {token[:4]}...")
            return await auth_service.verify_token(token)
        cookie_token = request.cookies.get("auth_token")
        if cookie_token:
            logger.info(f"Authentication check successful by cookie_token: {cookie_token[:4]}...")
            return await auth_service.verify_token(cookie_token)

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_cookie_user(
        request: Request,
        session_id: Optional[str] = Cookie(None, alias=COOKIE_NAME),
        csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token"),
        db: AsyncSession = Depends(get_async_db)
) -> Optional[User]:
    """
    Get the current user from cookie session.
    """
    if not session_id:
        return None

    auth_service = AuthService(db)

    try:
        # For GET requests, we don't enforce CSRF check
        if request.method == "GET":
            # Skip CSRF verification for GET requests
            session = await auth_service.validate_session(session_id)
            if session:
                user_id = session.get("user_id")
                return await auth_service.user_repo.get_by_id(user_id)
            return None

        # For non-GET requests, enforce CSRF protection
        if not csrf_token:
            logger.warning(f"Missing CSRF token for session: {session_id[:8]}...")
            return None

        # Verify session and CSRF token
        return await auth_service.verify_session(session_id, csrf_token)
    except Exception as e:
        logger.error(f"Cookie authentication error: {str(e)}")
        return None


async def get_current_active_user(
        token_user: Optional[User] = Depends(get_current_user),
        cookie_user: Optional[User] = Depends(get_cookie_user),
        db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Check if the current user is active. Supports both token and cookie auth.

    Args:
        token_user: User from token authentication
        cookie_user: User from cookie authentication
        db: Database session

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive or unauthorized
    """
    # Prioritize API token auth over cookie auth
    current_user = token_user or cookie_user

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Check if the current user is an admin.

    Args:
        current_user: Current user object

    Returns:
        User object if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user attempted admin access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    logger.info(f"Admin user authenticated: {current_user.username}")
    return current_user
