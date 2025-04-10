# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.adapters.auth.service import AuthService
from app.infrastructure.database.repository import get_async_db
from app.infrastructure.database.db_models import User
from app.api.schemas.auth import TokenResponse, LoginRequest, SessionResponse
from app.api.schemas.user import UserResponse, UserCreate
from app.api.middleware_auth import get_current_active_user
from app.utils.logger_util import get_logger
from app.utils.security import (
    create_session_cookie,
    set_csrf_cookie,
    generate_csrf_token,
    clear_auth_cookies,
    COOKIE_NAME,
    CSRF_COOKIE_NAME
)

# Configure logger
logger = get_logger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Register a new user."""
    auth_service = AuthService(db)

    user, error = await auth_service.register_user(
        user_data.username,
        str(user_data.email),
        user_data.password
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return user


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_async_db)
):
    """Generate an access token."""
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expire = await auth_service.create_user_token(user.id, user.username)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating token"
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expire,
        "user_id": user.id,
        "username": user.username
    }


@router.post("/logout")
async def logout(
        response: Response,
        request: Request,
        current_user: Optional[User] = Depends(get_current_active_user),
        token: Optional[str] = Depends(oauth2_scheme),
        session_id: Optional[str] = Cookie(None, alias=COOKIE_NAME),
        db: AsyncSession = Depends(get_async_db)
):
    """Logout by invalidating the token and/or session cookie."""
    auth_service = AuthService(db)

    # Clear session cookies
    clear_auth_cookies(response)

    # If API token provided, invalidate it
    if token and current_user:
        success = await auth_service.logout_user(current_user.id, token)
        if not success:
            logger.warning(f"Failed to invalidate token for user {current_user.id}")

    # If session cookie provided, invalidate it
    if session_id:
        await auth_service.invalidate_session(session_id)

    return {"detail": "Successfully logged out"}




@router.get("/me", response_model=UserResponse)
async def read_users_me(
        current_user: User = Depends(get_current_active_user)
):
    """Get current user info."""
    logger.info(f"User profile accessed: {current_user.username}")
    return current_user


# @router.post("/login", response_model=TokenResponse)
# async def login(
#         response: Response,
#         login_data: LoginRequest,
#         db: AsyncSession = Depends(get_async_db)
# ):
#     """Generate an access token using email/password."""
#     auth_service = AuthService(db)
#
#     user = await auth_service.authenticate_user(login_data.email, login_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#         )
#
#     access_token, expire = await auth_service.create_user_token(user.id, user.username)
#     if not access_token:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error creating token"
#         )
#
#     return {
#         "access_token": access_token,
#         "token_type": "bearer",
#         "expires_at": expire,
#         "user_id": user.id,
#         "username": user.username
#     }


@router.post("/login", response_model=SessionResponse)
async def login(
        response: Response,
        request: Request,
        login_data: LoginRequest,
        db: AsyncSession = Depends(get_async_db)
):
    """Login for web interface with cookie-based authentication."""
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Create session
    session_id, csrf_token, expire = await auth_service.create_user_session(
        user.id,
        user.username,
        remember=login_data.remember,
        request=request  # ← Pass the FastAPI Request
    )

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating session"
        )

    # Set cookies
    create_session_cookie(response, session_id, expire, True, True)
    set_csrf_cookie(response, csrf_token, False, True)
    await auth_service.activity_repo.create_activity(user.id, "login", "User logged in")
    return {
        "csrf_token": csrf_token,
        "expires_at": expire,
        "user_id": user.id,
        "username": user.username
    }


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Refresh an access token."""
    auth_service = AuthService(db)

    access_token, expire = await auth_service.create_user_token(current_user.id, current_user.username)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating token"
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expire,
        "user_id": current_user.id,
        "username": current_user.username
    }


@router.post("/refresh-csrf")
async def refresh_csrf(
        response: Response,
        request: Request,
        current_user: User = Depends(get_current_active_user),
        session_id: str = Cookie(..., alias=COOKIE_NAME)
):
    """Generate a new CSRF token for the current session."""
    # Generate a new CSRF token
    csrf_token = generate_csrf_token()

    # Set the new CSRF cookie
    set_csrf_cookie(response, csrf_token, False, True)

    logger.info(f"CSRF token refreshed for user {current_user.username}")

    return {
        "csrf_token": csrf_token,
        "user_id": current_user.id,
        "username": current_user.username
    }

@router.post("/refresh-session", response_model=SessionResponse)
async def refresh_session(
        response: Response,
        request: Request,
        session_id: str = Cookie(..., alias=COOKIE_NAME),
        db: AsyncSession = Depends(get_async_db)
):
    """Refresh a session for web interface."""
    auth_service = AuthService(db)

    # Verify and refresh session
    user_id, username, new_session_id, csrf_token, expire = await auth_service.refresh_session(session_id)

    if not new_session_id:
        # Clear invalid cookies
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    # Set new cookies
    create_session_cookie(response, new_session_id, expire, True, True)
    set_csrf_cookie(response, csrf_token, False, True)

    return {
        "csrf_token": csrf_token,
        "expires_at": expire,
        "user_id": user_id,
        "username": username
    }


@router.post("/reset-password")
async def request_password_reset(
        email_data: dict,
        db: AsyncSession = Depends(get_async_db)
):
    """Send password reset link to user's email."""
    auth_service = AuthService(db)

    email = email_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )

    success = await auth_service.request_password_reset(email)
    if not success:
        # Don't reveal if email exists or not for security
        logger.info(f"Password reset requested for non-existent email: {email}")

    # Always return success to prevent email enumeration
    return {"detail": "If your email is registered, you will receive a password reset link"}