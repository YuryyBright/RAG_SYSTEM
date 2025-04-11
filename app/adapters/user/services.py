import asyncio
import tempfile
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import os
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from app.api.schemas.user_api import (
    ProfileUpdate, PasswordChange, ApiKeyCreate, ApiKeyResponse,
    UserStats, UserActivityResponse, SessionInfo, NotificationSettings
)
from app.infrastructure.database.db_models import User, Token, UserActivity
# TODO IT later
# ApiKey, UserNotificationSettings)
from app.infrastructure.database.repository.user_repository import UserRepository
from app.infrastructure.database.repository.activity_repository import ActivityRepository
from app.infrastructure.database.repository.token_repository import TokenRepository
from app.utils.security import verify_password, get_password_hash, generate_api_key
from infrastructure.database.repository.session_repository import SessionRepository
from utils.logger_util import get_logger

logger = get_logger(__name__)


class UserService:
    """
    Service class responsible for managing user-related operations
    such as profile updates, password changes, token management,
    avatar uploads, user stats, and user activity tracking.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the UserService with the database session.
        """
        self.db = db
        self.user_repo = UserRepository(db)
        self.activity_repo = ActivityRepository(db)
        self.token_repo = TokenRepository(db)
        self.session_repo = SessionRepository(db)

    async def get_user_profile(self, user: User) -> Dict[str, Any]:
        """
        Get detailed user profile information.

        Parameters
        ----------
        user : User
            The user whose profile to retrieve.

        Returns
        -------
        Dict[str, Any]
            User profile data.
        """
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "timezone": user.timezone,
            "theme": user.theme,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        }

        # Record this activity
        await self.activity_repo.create_activity(user.id, "profile_view", "Viewed profile information")

        return user_data

    async def update_profile(self, user: User, data: ProfileUpdate):
        """
        Update the user's profile information.

        Parameters
        ----------
        user : User
            The user object to update.
        data : ProfileUpdate
            The profile update data.

        Raises
        ------
        HTTPException
            If the email is already registered to another user.
        """
        if await self.user_repo.email_exists(data.email) and data.email != user.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        await self.user_repo.update_user_profile(user, data.name, data.email, data.timezone, data.theme)
        await self.activity_repo.create_activity(user.id, "profile_update", "Updated profile information")

    async def change_password(self, user: User, data: PasswordChange):
        """
        Change the user's password.

        Parameters
        ----------
        user : User
            The user object whose password is being changed.
        data : PasswordChange
            The password change data.

        Raises
        ------
        HTTPException
            If the current password is incorrect.
        """
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

        hashed_password = get_password_hash(data.new_password)
        await self.user_repo.update_password(user.id, hashed_password)
        await self.activity_repo.create_activity(user.id, "password_change", "Changed account password")

    async def create_api_key(self, user: User, data: ApiKeyCreate) -> ApiKeyResponse:
        """
        Create a new API key for the user.

        Parameters
        ----------
        user : User
            The user for whom to create the key.
        data : ApiKeyCreate
            API key creation data.

        Returns
        -------
        ApiKeyResponse
            Created API key details.
        """
        # Generate a unique API key
        key_value = generate_api_key()

        # Create the API key record
        api_key = ApiKey(
            user_id=user.id,
            name=data.name,
            key_hash=get_password_hash(key_value),  # Store a hash of the key value
            expires_at=datetime.utcnow() + timedelta(days=data.expires_days) if data.expires_days else None
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        # Log the activity
        await self.activity_repo.create_activity(
            user.id,
            "api_key_created",
            f"Created API key: {data.name}"
        )

        # Return the API key info with the plaintext key value
        # This is the only time we'll return the actual key value
        return ApiKeyResponse(
            id=api_key.id,
            name=api_key.name,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            last_used=None,
            key=key_value  # Only provided upon creation
        )

    async def get_api_keys(self, user: User) -> List[ApiKeyResponse]:
        """
        Get all API keys for a user.

        Parameters
        ----------
        user : User
            The user whose API keys to retrieve.

        Returns
        -------
        List[ApiKeyResponse]
            List of API keys belonging to the user.
        """
        # Query all active API keys for the user
        query = f"""
            SELECT id, name, created_at, expires_at, last_used
            FROM api_keys
            WHERE user_id = :user_id
            AND (expires_at IS NULL OR expires_at > :now)
            ORDER BY created_at DESC
        """

        result = await self.db.execute(
            query,
            {"user_id": user.id, "now": datetime.utcnow()}
        )
        api_keys = result.fetchall()

        return [
            ApiKeyResponse(
                id=key.id,
                name=key.name,
                created_at=key.created_at,
                expires_at=key.expires_at,
                last_used=key.last_used,
                key=None  # We never return the key after creation
            )
            for key in api_keys
        ]

    async def delete_api_key(self, user: User, key_id: int):
        """
        Delete an API key.

        Parameters
        ----------
        user : User
            The user who owns the key.
        key_id : int
            The ID of the API key to delete.

        Raises
        ------
        HTTPException
            If the key doesn't exist or doesn't belong to the user.
        """
        # Check that the key exists and belongs to the user
        query = f"""
            SELECT id, name FROM api_keys
            WHERE id = :key_id AND user_id = :user_id
        """
        result = await self.db.execute(query, {"key_id": key_id, "user_id": user.id})
        key = result.fetchone()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Delete the key
        delete_query = f"""
            DELETE FROM api_keys
            WHERE id = :key_id
        """
        await self.db.execute(delete_query, {"key_id": key_id})
        await self.db.commit()

        # Log the activity
        await self.activity_repo.create_activity(
            user.id,
            "api_key_deleted",
            f"Deleted API key: {key.name}"
        )

    async def get_active_sessions(self, user: User) -> List[SessionInfo]:
        """
        Get all active sessions for a user.

        Parameters
        ----------
        user : User
            The user whose sessions to retrieve.

        Returns
        -------
        List[SessionInfo]
            List of active user sessions.
        """
        sessions = await self.session_repo.get_active_sessions(user.id)
        print(sessions)
        return [
            SessionInfo(
                id=session.id,
                device=session.device,
                browser=session.browser,
                os=session.os,
                ip_address=session.ip_address,
                location=session.location,
                created_at=session.created_at,
                last_activity=session.last_accessed,
                is_current=session.is_current
            )
            for session in sessions
        ]

    async def revoke_session(self, user: User, session_id: str):
        """
        Revoke a specific session.

        Parameters
        ----------
        user : User
            The user who owns the session.
        session_id : str
            The ID of the session to revoke.

        Raises
        ------
        HTTPException
            If the session doesn't exist or doesn't belong to the user.
        """
        success = await self.session_repo.revoke_session(user.id, session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        await self.activity_repo.create_activity(
            user.id,
            "session_revoked",
            f"Revoked session ID: {session_id}"
        )

    async def revoke_all_sessions(self, user: User, current_session_id: str):
        """
        Revoke all sessions except the current one.

        Parameters
        ----------
        user : User
            The user whose sessions to revoke.
        current_session_id : str
            The ID of the session to preserve.
        """
        await self.session_repo.revoke_all_other_sessions(user.id, current_session_id)

        await self.activity_repo.create_activity(
            user.id,
            "all_sessions_revoked",
            "Revoked all other active sessions"
        )

    async def deactivate_user(self, user: User):
        """
        Deactivate a user's account.

        Parameters
        ----------
        user : User
            The user object to deactivate.
        """
        user.is_active = False
        await self.db.commit()
        await self.activity_repo.create_activity(user.id, "account_deactivation", "Deactivated account")

    async def reactivate_user(self, user: User):
        """
        Reactivate a user's account.

        Parameters
        ----------
        user : User
            The user object to reactivate.
        """
        user.is_active = True
        await self.db.commit()
        await self.activity_repo.create_activity(user.id, "account_reactivation", "Reactivated account")

    async def get_user_activity(
            self,
            user: User,
            limit: int = 10,
            offset: int = 0,
            activity_type: Optional[str] = None
    ) -> List[UserActivityResponse]:
        """
        Retrieve the user's recent activity with optional filtering and pagination.

        Parameters
        ----------
        user : User
            The user whose activity to fetch.
        limit : int
            Max number of activities.
        offset : int
            Number of records to skip (for pagination).
        activity_type : str, optional
            Optional filter by activity type.

        Returns
        -------
        List[UserActivityResponse]
            List of activity entries.
        """
        # Use different repository methods based on filter
        if activity_type:
            activities = await self.activity_repo.get_user_activities(
                user.id, activity_type=activity_type, offset=offset, limit=limit
            )
        else:
            activities = await self.activity_repo.get_user_activities(
                user.id, offset=offset, limit=limit
            )

        return [
            UserActivityResponse(
                id=a.id,
                type=a.activity_type,
                description=a.description,
                timestamp=a.timestamp
            ) for a in activities
        ]

    async def get_user_stats(self, user: User, period: str = "month") -> UserStats:
        """
        Get usage statistics for a user.

        Parameters
        ----------
        user : User
            The user to get stats for.
        period : str
            The time period for stats: "week", "month", "year", or "all".

        Returns
        -------
        UserStats
            User usage statistics.
        """
        # Define the start date based on the period
        now = datetime.utcnow()
        if period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        elif period == "year":
            start_date = now - timedelta(days=365)
        else:  # "all"
            start_date = datetime(1970, 1, 1)  # Unix epoch

        # Get query usage stats by day
        query_stats = await self.activity_repo.get_activity_counts_by_date(
            user.id,
            "query",
            start_date
        )

        # Get document stats (count by document type)
        # This would need to be implemented based on your document model
        doc_stats = {
            "labels": ["PDF", "Word", "Text", "Other"],
            "data": [10, 5, 15, 2]  # Placeholder data
        }
        activity_counts_list = await self.activity_repo.get_activity_counts_by_type(
            user.id,
            start_date
        )
        # Get total counts for different activities
        activity_counts = {item["type"]: item["count"] for item in activity_counts_list}

        # Create the response
        return UserStats(
            query_stats=query_stats,
            doc_stats=doc_stats,
            file_count=25,  # Placeholder
            login_count=activity_counts.get("login", 0),
            query_count=activity_counts.get("query", 0),
            upload_count=activity_counts.get("file_upload", 0)
        )

    async def update_avatar(self, user: User, avatar_url: str):
        """
        Update the user's avatar.

        Parameters
        ----------
        user : User
            The user object whose avatar is being updated.
        avatar_url : str
            The new avatar URL.
        """
        await self.user_repo.update_avatar_url(user, avatar_url)
        await self.activity_repo.create_activity(user.id, "avatar_update", "Updated profile picture")

    async def reset_avatar(self, user: User):
        """
        Reset the user's avatar to the default.

        Parameters
        ----------
        user : User
            The user whose avatar to reset.
        """
        # First, delete the current avatar file if it exists
        if user.avatar_url and user.avatar_url.startswith("/static/uploads/avatars/"):
            avatar_path = Path(user.avatar_url.replace("/static/", "static/"))
            if os.path.exists(avatar_path):
                try:
                    os.remove(avatar_path)
                except Exception as e:
                    logger.warning(f"Failed to delete avatar file: {str(e)}")

        # Set the default avatar URL
        default_avatar = "/static/dist/img/user.png"
        await self.user_repo.update_avatar_url(user, default_avatar)
        await self.activity_repo.create_activity(user.id, "avatar_reset", "Reset profile picture to default")

    async def update_notification_settings(self, user: User, settings: NotificationSettings):
        """
        Update user notification preferences.

        Parameters
        ----------
        user : User
            The user whose notification settings to update.
        settings : NotificationSettings
            The new notification settings.
        """
        # Get or create notification settings for the user
        query = f"""
            SELECT id FROM user_notification_settings
            WHERE user_id = :user_id
        """
        result = await self.db.execute(query, {"user_id": user.id})
        settings_record = result.fetchone()

        if settings_record:
            # Update existing settings
            update_query = f"""
                UPDATE user_notification_settings
                SET 
                    email_notifications = :email_notifications,
                    browser_notifications = :browser_notifications,
                    login_alerts = :login_alerts,
                    api_usage_alerts = :api_usage_alerts,
                    file_activity_notifications = :file_activity_notifications
                WHERE user_id = :user_id
            """
        else:
            # Create new settings
            update_query = f"""
                INSERT INTO user_notification_settings 
                (user_id, email_notifications, browser_notifications, login_alerts, 
                api_usage_alerts, file_activity_notifications)
                VALUES 
                (:user_id, :email_notifications, :browser_notifications, :login_alerts,
                :api_usage_alerts, :file_activity_notifications)
            """

        await self.db.execute(
            update_query,
            {
                "user_id": user.id,
                "email_notifications": settings.email_notifications,
                "browser_notifications": settings.browser_notifications,
                "login_alerts": settings.login_alerts,
                "api_usage_alerts": settings.api_usage_alerts,
                "file_activity_notifications": settings.file_activity_notifications
            }
        )
        await self.db.commit()

        await self.activity_repo.create_activity(
            user.id,
            "notification_settings_update",
            "Updated notification preferences"
        )

    async def schedule_data_export(self, user: User, background_tasks: BackgroundTasks) -> str:
        """
        Schedule a data export job for a user.

        Parameters
        ----------
        user : User
            The user requesting the export.
        background_tasks : BackgroundTasks
            FastAPI background tasks system.

        Returns
        -------
        str
            Job ID for tracking export progress.
        """
        # Generate a unique job ID
        job_id = str(uuid.uuid4())

        # Create export directory if it doesn't exist
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        # Create job status file
        status_file = export_dir / f"{job_id}.status"
        with open(status_file, "w") as f:
            json.dump({
                "status": "pending",
                "user_id": user.id,
                "created_at": datetime.utcnow().isoformat(),
                "progress": 0
            }, f)

        # Schedule the background task
        background_tasks.add_task(self._process_data_export, user, job_id)

        # Record the activity
        await self.activity_repo.create_activity(
            user.id,
            "data_export_requested",
            "Requested data export"
        )

        return job_id

    async def generate_data_export(self, user: User) -> FileResponse:
        """
        Generate a data export for a user and return the file for immediate download.
        """
        # Simulated data
        export_data = {
            "user_id": user.id,
            "email": user.email,
            "exported_at": datetime.utcnow().isoformat()
        }

        # File path
        export_id = str(uuid.uuid4())
        filename = f"user_export_{user.id}.json"
        export_path = Path(tempfile.gettempdir()) / filename

        # Write JSON export
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)



        # Log activity
        await self.activity_repo.create_activity(
            user.id,
            "data_export_downloaded",
            "Downloaded user data export"
        )

        # Return the actual file as response
        return FileResponse(
            path=export_path,
            filename=filename,
            media_type="application/json"
        )
    async def _process_data_export(self, user: User, job_id: str) -> None:
        """
        Background task to process data export.

        Parameters
        ----------
        user : User
            The user for whom data is being exported.
        job_id : str
            The unique job identifier.
        """
        status_file = Path("exports") / f"{job_id}.status"

        try:
            # Simulate export steps
            for progress in range(0, 101, 20):
                await asyncio.sleep(1)  # Simulate time-consuming export work

                with open(status_file, "w") as f:
                    json.dump({
                        "status": "in_progress" if progress < 100 else "completed",
                        "user_id": user.id,
                        "updated_at": datetime.utcnow().isoformat(),
                        "progress": progress
                    }, f)

            # Optionally notify the user or update other systems
        except Exception as e:
            with open(status_file, "w") as f:
                json.dump({
                    "status": "failed",
                    "user_id": user.id,
                    "updated_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }, f)
    async def check_export_status(self, user: User, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a data export job.

        Parameters
        ----------
        user : User
            The user who requested the export.
        job_id : str
            The export job ID.

        Returns
        -------
        Dict[str, Any]
            Status information of the export job.

        Raises
        ------
        HTTPException
            If the job does not exist or does not belong to the user.
        """
        status_file = Path("exports") / f"{job_id}.status"
        if not status_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")

        with open(status_file, "r") as f:
            job_status = json.load(f)

        if job_status["user_id"] != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this export job")

        return job_status
