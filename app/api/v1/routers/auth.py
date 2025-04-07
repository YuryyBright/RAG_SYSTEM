# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid

from app.adapters.auth.security import get_password_hash, authenticate_user, create_access_token, get_current_active_user
from app.infrastructure.database.repository import get_db
from app.infrastructure.database.db_models import User, Token
from app.config import settings

from app.api.schemas.auth import TokenResponse
from app.api.schemas.user import UserResponse, UserCreate

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if username or email already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if db.query(User).filter(User.email == user_data.email).first():
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
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
    db.add(db_token)
    db.commit()

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
        db.delete(db_token)
        db.commit()
    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    return current_user