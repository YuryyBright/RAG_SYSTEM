# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid

from app.infrastructure.database.repository import get_db
from app.infrastructure.database.db_models import User, Token
from app.config import settings
from app.api.schemas.auth import TokenResponse
from app.api.schemas.user import UserResponse, UserCreate
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.adapters.auth.security import JWTAuth
from app.utils.logger_util import get_logger

# Configure logger
logger = get_logger(__name__)

router = APIRouter()
auth_service = JWTAuth()


def authenticate_user(db: Session, username: str, password: str):
    """
    Authenticate a user by username and password.

    Args:
        db: Database session
        username: Username or email
        password: Plain password

    Returns:
        User object if authenticated, None otherwise
    """
    # Check if the username is actually an email
    if '@' in username:
        user = db.query(User).filter(User.email == username).first()
    else:
        user = db.query(User).filter(User.username == username).first()

    if not user:
        logger.info(f"Authentication attempt for non-existent user: {username}")
        return None

    if not verify_password(password, user.hashed_password):
        logger.info(f"Failed login attempt for user: {username}")
        return None

    logger.info(f"User authenticated successfully: {username}")
    return user


def get_current_active_user(db: Session = Depends(get_db), token: str = Depends(OAuth2PasswordRequestForm)):
    """
    Get the current active user from token.

    Args:
        db: Database session
        token: JWT token

    Returns:
        User object if token is valid

    Raises:
        HTTPException: If token is invalid or user is inactive
    """
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if username or email already exists
    if db.query(User).filter(User.username == user_data.username).first():
        logger.warning(f"Registration attempt with existing username: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if db.query(User).filter(User.email == user_data.email).first():
        logger.warning(f"Registration attempt with existing email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        id=str(uuid.uuid4()),
        username=user_data.username,
        email=str(user_data.email),  # Convert EmailStr to str
        hashed_password=hashed_password,
        is_active=True
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User registered successfully: {user.username}")
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user"
        )


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """Generate an access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token
    access_token, expire = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    )

    # Store token in database
    db_token = Token(
        id=str(uuid.uuid4()),
        token=access_token,
        user_id=user.id,
        expires_at=expire
    )

    try:
        db.add(db_token)
        db.commit()
        logger.info(f"Access token created for user: {user.username}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing token: {e}")
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
        token: str = Depends(OAuth2PasswordRequestForm),
        db: Session = Depends(get_db)
):
    """Logout by invalidating the token."""
    db_token = db.query(Token).filter(Token.token == token, Token.user_id == current_user.id).first()

    if db_token:
        try:
            db.delete(db_token)
            db.commit()
            logger.info(f"User logged out successfully: {current_user.username}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error during logout: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error logging out"
            )
    else:
        logger.warning(f"Logout attempt with invalid token for user: {current_user.username}")

    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    logger.info(f"User profile accessed: {current_user.username}")
    return current_user