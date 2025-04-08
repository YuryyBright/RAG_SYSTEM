# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repository import get_async_db
from app.infrastructure.database.db_models import User
from app.api.schemas.auth import TokenResponse, LoginRequest
from app.api.schemas.user import UserResponse, UserCreate
from app.api.middleware_auth import get_current_active_user
from app.adapters.auth.security import AuthService
from app.utils.logger_util import get_logger

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
        current_user: User = Depends(get_current_active_user),
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_async_db)
):
    """Logout by invalidating the token."""
    auth_service = AuthService(db)

    success = await auth_service.logout_user(current_user.id, token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging out"
        )

    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    logger.info(f"User profile accessed: {current_user.username}")
    return current_user


@router.post("/login", response_model=TokenResponse)
async def login(
        login_data: LoginRequest,
        db: AsyncSession = Depends(get_async_db)
):
    """Generate an access token using email/password."""
    auth_service = AuthService(db)

    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
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