# app/api/routes/user_api.py
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.user.services import UserService
from app.api.schemas.user_api import ProfileUpdate, PasswordChange, ApiKeyResponse, ApiKeyCreate, UserStats
from app.infrastructure.database.db_models import User
from app.infrastructure.database.repository import get_async_db
from app.api.middleware_auth import get_current_active_user


router = APIRouter()


@router.put("/profile", response_model=dict)
async def update_profile(
        profile_data: ProfileUpdate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Update user profile information."""
    service = UserService(db)
    await service.update_profile(current_user, profile_data)
    return {"status": "success", "message": "Profile updated successfully"}


@router.post("/change-password", response_model=dict)
async def change_password(
        password_data: PasswordChange,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Change the current user's password."""
    service = UserService(db)
    await service.change_password(current_user, password_data)
    return {"status": "success", "message": "Password changed successfully"}


# @router.post("/apikeys", response_model=ApiKeyResponse)
# async def create_api_key(
#         key_data: ApiKeyCreate,
#         current_user: User = Depends(get_current_active_user),
#         db: AsyncSession = Depends(get_async_db)
# ):
#     """Create a new API key for the user."""
#     service = UserService(db)
#     return await service.create_api_key(current_user, key_data)
#
#
# @router.get("/apikeys", response_model=List[ApiKeyResponse])
# async def get_api_keys(
#         current_user: User = Depends(get_current_active_user),
#         db: AsyncSession = Depends(get_async_db)
# ):
#     """Retrieve all API keys for the user."""
#     service = UserService(db)
#     return await service.get_api_keys(current_user)


# @router.delete("/apikeys/{key_id}", response_model=dict)
# async def delete_api_key(
#         key_id: int,
#         current_user: User = Depends(get_current_active_user),
#         db: AsyncSession = Depends(get_async_db)
# ):
#     """Delete an API key owned by the current user."""
#     service = UserService(db)
#     await service.delete_api_key(current_user, key_id)
#     return {"status": "success", "message": "API key deleted"}


@router.get("/activity", response_model=dict)
async def get_user_activity(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
        limit: int = 10
):
    """Fetch recent user activity."""
    service = UserService(db)
    activities = await service.get_user_activity(current_user, limit)
    return {"activities": [activity.dict() for activity in activities]}


# @router.get("/stats", response_model=UserStats)
# async def get_user_stats(
#         current_user: User = Depends(get_current_active_user),
#         db: AsyncSession = Depends(get_async_db)
# ):
#     """Retrieve usage statistics for the current user."""
#     service = UserService(db)
#     return await service.get_user_stats(current_user)


AVATAR_DIR = Path("static/uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/avatar", status_code=status.HTTP_200_OK)
async def upload_avatar(
        avatar: UploadFile = File(...),
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Upload a new avatar image for the user."""
    allowed_types = ["image/jpeg", "image/png", "image/gif"]
    if avatar.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and GIF images are allowed"
        )

    filename = f"{current_user.id}_{uuid4()}{Path(avatar.filename).suffix}"
    file_path = AVATAR_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(avatar.file, buffer)

    avatar_url = f"/static/uploads/avatars/{filename}"
    service = UserService(db)
    await service.update_avatar(current_user, avatar_url)

    return {"status": "success", "avatar_url": avatar_url}
