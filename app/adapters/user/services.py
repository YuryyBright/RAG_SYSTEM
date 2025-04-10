from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.api.schemas.user_api import (
    ProfileUpdate, PasswordChange, ApiKeyCreate,
    ApiKeyResponse, UserStats, UserActivityResponse
)
from app.infrastructure.database.db_models import User, Token
from app.infrastructure.database.repository.user_repository import UserRepository
from app.infrastructure.database.repository.activity_repository import ActivityRepository
from app.infrastructure.database.repository.token_repository import TokenRepository
from app.utils.security import verify_password, get_password_hash, generate_api_key
class UserService:
    """
    Service class responsible for managing user-related operations
    such as profile updates, password changes, token management,
    avatar uploads, user stats, and user activity tracking.

    Attributes
    ----------
    db : AsyncSession
        The async database session.
    user_repo : UserRepository
        Handles user persistence logic.
    activity_repo : ActivityRepository
        Handles tracking of user actions.
    token_repo : TokenRepository
        Handles token-level operations such as revocation.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the UserService with the database session.

        Parameters
        ----------
        db : AsyncSession
            The async database session.
        """
        self.db = db
        self.user_repo = UserRepository(db)
        self.activity_repo = ActivityRepository(db)
        self.token_repo = TokenRepository(db)

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

    async def get_user_activity(self, user: User, limit: int = 10) -> List[UserActivityResponse]:
        """
        Retrieve the user's recent activity.

        Parameters
        ----------
        user : User
            The user object whose activity is being retrieved.
        limit : int, optional
            The maximum number of activities to retrieve (default is 10).

        Returns
        -------
        List[UserActivityResponse]
            A list of user activity responses.
        """
        activities = await self.activity_repo.get_user_activities(user.id, limit=limit)
        return [
            UserActivityResponse(
                id=a.id,
                type=a.activity_type,
                description=a.description,
                timestamp=a.timestamp
            ) for a in activities
        ]

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

    async def delete_user(self, user: User):
        """
        Permanently delete a user's account.

        Parameters
        ----------
        user : User
            The user object to delete.
        """
        await self.user_repo.delete_user(user)
        await self.activity_repo.create_activity(user.id, "account_deletion", "Deleted account")