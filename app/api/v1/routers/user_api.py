# app/api/routes/user_api.py
import shutil
import os
from pathlib import Path
from uuid import uuid4
from typing import List, Optional

from fastapi import APIRouter, Request, Depends, HTTPException, status, UploadFile, File, Query, \
    BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user.services import UserService
from app.api.schemas.user_api import (
    ProfileUpdate, PasswordChange, AccountAction, SessionInfo, NotificationSettings
)
from app.infrastructure.database.db_models import User
from infrastructure.repositories import get_async_db
from app.api.middleware_auth import get_current_active_user, get_session_id_from_cookie
from utils.logger_util import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/me", response_model=dict)
async def get_profile(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Get the current user's profile information."""
    service = UserService(db)
    user_data = await service.get_user_profile(current_user)
    return user_data


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

@router.get("/activity", response_model=dict)
async def get_user_activity(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    activity_type: Optional[str] = None
):
    """
    Fetch paginated recent user activity with optional filtering.
    """
    service = UserService(db)
    offset = (page - 1) * limit
    activities = await service.get_user_activity(current_user, limit=limit, activity_type=activity_type, offset=offset)
    return {"activities": [activity.dict() for activity in activities]}

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
#
#
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

# @router.get("/stats", response_model=UserStats)
# async def get_user_stats(
#         current_user: User = Depends(get_current_active_user),
#         db: AsyncSession = Depends(get_async_db),
#         period: Optional[str] = Query("month", regex="^(week|month|year|all)$")
# ):
#     """Retrieve usage statistics for the current user."""
#     service = UserService(db)
#     return await service.get_user_stats(current_user, period)


@router.get("/sessions", response_model=List[SessionInfo])
async def get_active_sessions(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Get all active sessions for the current user."""
    service = UserService(db)
    return await service.get_active_sessions(current_user)


@router.delete("/sessions/{id}", response_model=dict)
async def revoke_session(
    id:  str,  # ✅ correct!
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Revoke a specific session by session ID (from URL path).
    """
    service = UserService(db)
    await service.revoke_session(current_user, id)
    return {"status": "success", "message": "Session revoked successfully"}





@router.delete("/sessions", response_model=dict)
async def revoke_all_sessions(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Revoke all sessions except the current one.
    The current session ID is extracted from cookies.
    """
    session_id = get_session_id_from_cookie(request)

    service = UserService(db)
    await service.revoke_all_sessions(current_user, session_id)
    return {"status": "success", "message": "All other sessions revoked successfully"}







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
    max_size = 5 * 1024 * 1024  # 5MB

    if avatar.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and GIF images are allowed"
        )

    # Read the file first to check size
    contents = await avatar.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image size exceeds the maximum limit of 5MB"
        )

    # Reset file pointer
    await avatar.seek(0)

    # Clean up old avatar if exists
    if current_user.avatar_url and current_user.avatar_url != "/static/dist/img/user.png":
        old_avatar_path = Path(current_user.avatar_url.replace("/static/", "static/"))
        if os.path.exists(old_avatar_path):
            try:
                os.remove(old_avatar_path)
            except Exception as e:
                logger.warning(f"Failed to delete old avatar: {str(e)}")

    filename = f"{current_user.id}_{uuid4()}{Path(avatar.filename).suffix}"
    file_path = AVATAR_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(avatar.file, buffer)

    avatar_url = f"/static/uploads/avatars/{filename}"
    service = UserService(db)
    await service.update_avatar(current_user, avatar_url)

    return {"status": "success", "avatar_url": avatar_url}


@router.delete("/avatar", response_model=dict)
async def remove_avatar(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Remove the user's avatar and reset to default."""
    service = UserService(db)
    await service.reset_avatar(current_user)
    return {"status": "success", "message": "Avatar removed successfully"}


@router.put("/notifications", response_model=dict)
async def update_notification_settings(
        settings: NotificationSettings,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Update user notification preferences."""
    service = UserService(db)
    await service.update_notification_settings(current_user, settings)
    return {"status": "success", "message": "Notification settings updated"}


@router.post("/account", response_model=dict)
async def account_action(
        action: AccountAction,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Perform account action (deactivate/reactivate)."""
    service = UserService(db)

    if action.action == "deactivate":
        await service.deactivate_user(current_user)
        return {"status": "success", "message": "Account deactivated successfully"}
    elif action.action == "reactivate":
        await service.reactivate_user(current_user)
        return {"status": "success", "message": "Account reactivated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action specified"
        )


@router.get("/export", response_model=dict)
async def request_data_export(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Request an export of all user data."""
    service = UserService(db)
    return await service.generate_data_export(current_user)


@router.get("/export/{job_id}", response_model=dict)
async def check_export_status(
        job_id: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Check the status of a data export job."""
    service = UserService(db)
    status_info = await service.check_export_status(current_user, job_id)
    return status_info