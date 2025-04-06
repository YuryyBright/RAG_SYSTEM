# app/auth/security.py
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.models.db_models import User, Token
from app.database import get_db
from app.config import settings
from schemas.users.login import TokenData

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 password bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Parameters
    ----------
    plain_password : str
        The plain text password.
    hashed_password : str
        The hashed password.

    Returns
    -------
    bool
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a password hash.

    Parameters
    ----------
    password : str
        The plain text password.

    Returns
    -------
    str
        The hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token.

    Parameters
    ----------
    data : dict
        The data to encode in the token.
    expires_delta : Optional[timedelta], optional
        The expiration time delta, by default None.

    Returns
    -------
    str
        The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, expire


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.

    Parameters
    ----------
    db : Session
        The database session.
    username : str
        The username.
    password : str
        The plain text password.

    Returns
    -------
    Optional[User]
        The authenticated user or None if authentication fails.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    """
    Get the current user from the token.

    Parameters
    ----------
    token : str
        The JWT token.
    db : Session
        The database session.

    Returns
    -------
    User
        The current user.

    Raises
    ------
    HTTPException
        If the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # Check if token exists in database and is not expired
    db_token = db.query(Token).filter(Token.token == token).first()
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Check if the current user is active.

    Parameters
    ----------
    current_user : User
        The current user.

    Returns
    -------
    User
        The current active user.

    Raises
    ------
    HTTPException
        If the user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user