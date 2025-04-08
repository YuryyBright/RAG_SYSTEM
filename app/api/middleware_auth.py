# app/api/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime

from app.infrastructure.database.repository import get_async_db
from app.infrastructure.database.db_models import User, Token
from app.adapters.auth.security import JWTAuth
from app.utils.logger_util import get_logger

# Configure logger
logger = get_logger(__name__)

# Setup OAuth2 with token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Initialize JWT auth service
auth_service = JWTAuth()


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_async_db)):
    """
    Get the current user from token.

    Args:
        token: JWT token
        db: Database session

    Returns:
        User object if token is valid

    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token is valid
    payload = auth_service.verify_token(token)
    if not payload:
        logger.warning(f"Invalid token provided")
        raise credentials_exception

    # Extract username (subject) from token
    username = payload.get("sub")
    if username is None:
        logger.warning(f"Token missing subject claim")
        raise credentials_exception

    # Check if token exists in database
    db_token = db.query(Token).filter(Token.token == token).first()
    if not db_token:
        logger.warning(f"Token not found in database")
        raise credentials_exception

    # Check if token has expired
    if db_token.expires_at < datetime.utcnow():
        logger.warning(f"Expired token used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"User from token not found: {username}")
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Check if the current user is active.

    Args:
        current_user: Current user object

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    logger.info(f"Active user authenticated: {current_user.username}")
    return current_user