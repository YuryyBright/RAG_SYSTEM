# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from fastapi import Header
from app.adapters.auth.service import AuthService
from app.infrastructure.database.repository import get_async_db
from app.infrastructure.database.db_models import User
from app.api.schemas.auth import TokenResponse, LoginRequest, SessionResponse
from app.api.schemas.user import UserResponse, UserCreate, UserInfo
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Logout the user using cookie-based session authentication and CSRF protection.

    This endpoint:
    - Reads session ID and CSRF token from cookies.
    - Verifies that the CSRF token matches the one stored in the session.
    - Invalidates the session on the server and clears client-side cookies.

    Args:
        response: HTTP response object to clear cookies.
        request: HTTP request object to read cookies.
        db: Async database session.

    Returns:
        JSON response indicating successful logout.

    Raises:
        HTTPException: If session is missing or CSRF validation fails.
    """
    auth_service = AuthService(db)

    session_id = request.cookies.get(COOKIE_NAME)
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME)

    if not session_id:
        logger.warning("Logout attempted without session cookie.")
        raise HTTPException(status_code=401, detail="No active session")

    if not csrf_token:
        logger.warning(f"Missing CSRF cookie for session {session_id[:8]}...")
        raise HTTPException(status_code=403, detail="Missing CSRF token")

    # Validate CSRF token against stored session token
    valid_csrf = await auth_service.get_csrf_token_for_session(session_id)
    if csrf_token != valid_csrf:
        logger.warning(f"CSRF token mismatch during logout for session {session_id[:8]}...")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    # Validate session and get current user
    current_user = await auth_service.verify_session(session_id, csrf_token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Clear cookies and invalidate session
    clear_auth_cookies(response)
    await auth_service.invalidate_session(session_id)
    await auth_service.activity_repo.create_activity(current_user.id, "logout", "User logged out")
    logger.info(f"User {current_user.username} logged out successfully")
    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user(
        request: Request,
        db = Depends(get_async_db),
):
    """Endpoint to verify authentication and get current user info."""

    auth_service = AuthService(db)
    try:
        # Check for session cookie
        session_id = request.cookies.get(COOKIE_NAME)
        if session_id:
            user = await auth_service.get_user_by_session_id(session_id)
            if not user:
                # Make sure we have a consistent error message when session isn't found
                raise HTTPException(status_code=401, detail="Session not found")

            # Return user info
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }

        # Check for token auth
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Extract token from Bearer format
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid authentication scheme")

            user = await auth_service.get_user_by_token(token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid token")

            # Return user info
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }

        # No authentication credentials found
        raise HTTPException(status_code=401, detail="Not authenticated")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=SessionResponse)
async def login(
        response: Response,
        request: Request,
        login_data: LoginRequest,
        db: AsyncSession = Depends(get_async_db)
):
    """Login for web interface with improved error handling and security."""
    auth_service = AuthService(db)

    try:
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account disabled",
            )

        # Create session with improved error handling
        session_id, csrf_token, expire = await auth_service.create_user_session(
            user.id,
            user.username,
            remember=login_data.remember,
            request=request
        )

        if not session_id or not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating session"
            )

        # Create JWT token and store it
        access_token, token_expiry = await auth_service.create_user_token(
            user.id, user.username
        )
        if not access_token:
            # Clean up the created session if token creation fails
            await auth_service.invalidate_session(session_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating access token"
            )

        # Set session and CSRF cookies
        create_session_cookie(response, session_id, expire, True, True)
        set_csrf_cookie(response, csrf_token, False, True)

        # Log the login activity
        await auth_service.activity_repo.create_activity(user.id, "login", "User logged in")
        logger.info(f"User {user.username} logged in successfully")

        return {
            "csrf_token": csrf_token,
            "expires_at": expire,
            "access_token": access_token,
            "access_token_expires_at": token_expiry,
            "user_id": user.id,
            "username": user.username
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


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
        session_id: str = Cookie(..., alias=COOKIE_NAME),
        db: AsyncSession = Depends(get_async_db)
):
    """Generate a new CSRF token for the current session and update it in storage."""
    auth_service = AuthService(db)

    # Generate a new CSRF token
    csrf_token = generate_csrf_token(session_id)

    # Update the CSRF token in the session storage
    updated = await auth_service.session_repo.update_session_csrf_token(session_id, csrf_token)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update CSRF token"
        )

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
    user_id, username, new_session_id, csrf_token, expire = await auth_service.refresh_session(
        session_id,
        request=request
    )


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