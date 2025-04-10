# app/infrastructure/database/repository/activity_repository.py
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.db_models import UserActivity


class ActivityRepository:
    """
    Repository for managing user activity records in the database.

    Provides asynchronous methods to create, retrieve, search, and delete
    user activity records.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the repository with a database session.

        Parameters
        ----------
        db : AsyncSession
            SQLAlchemy asynchronous session
        """
        self.db = db

    async def create_activity(self, user_id: str, activity_type: str, description: str) -> UserActivity:
        """
        Create a new user activity record.

        Parameters
        ----------
        user_id : str
            The ID of the user who performed the activity
        activity_type : str
            The type of activity (e.g., login, profile_update)
        description : str
            A detailed description of the activity

        Returns
        -------
        UserActivity
            The newly created user activity
        """
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            timestamp=datetime.utcnow()
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def get_activity_by_id(self, activity_id: int) -> Optional[UserActivity]:
        """
        Retrieve an activity by its ID.

        Parameters
        ----------
        activity_id : int
            The ID of the activity to retrieve

        Returns
        -------
        Optional[UserActivity]
            The user activity if found, otherwise None
        """
        stmt = select(UserActivity).where(UserActivity.id == activity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_activities(self, user_id: str, skip: int = 0, limit: int = 100) -> List[UserActivity]:
        """
        Retrieve user activities with pagination.

        Parameters
        ----------
        user_id : str
            The user ID whose activities are being retrieved
        skip : int
            Number of records to skip (pagination)
        limit : int
            Maximum number of records to return

        Returns
        -------
        List[UserActivity]
            List of activities for the user
        """
        stmt = (
            select(UserActivity)
            .where(UserActivity.user_id == user_id)
            .order_by(UserActivity.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_activities_by_type(self, activity_type: str, skip: int = 0, limit: int = 100) -> List[UserActivity]:
        """
        Retrieve activities filtered by type.

        Parameters
        ----------
        activity_type : str
            The type of activities to retrieve
        skip : int
            Number of records to skip (pagination)
        limit : int
            Maximum number of records to return

        Returns
        -------
        List[UserActivity]
            List of user activities of the specified type
        """
        stmt = (
            select(UserActivity)
            .where(UserActivity.activity_type == activity_type)
            .order_by(UserActivity.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_activities_by_date_range(
        self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100
    ) -> List[UserActivity]:
        """
        Retrieve activities that occurred between two timestamps.

        Parameters
        ----------
        start_date : datetime
            Start of the time range
        end_date : datetime
            End of the time range
        skip : int
            Number of records to skip (pagination)
        limit : int
            Maximum number of records to return

        Returns
        -------
        List[UserActivity]
            List of activities within the specified time range
        """
        stmt = (
            select(UserActivity)
            .where(UserActivity.timestamp >= start_date)
            .where(UserActivity.timestamp <= end_date)
            .order_by(UserActivity.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_activity(self, activity_id: int) -> bool:
        """
        Delete an activity by its ID.

        Parameters
        ----------
        activity_id : int
            The ID of the activity to delete

        Returns
        -------
        bool
            True if deleted, False otherwise
        """
        activity = await self.get_activity_by_id(activity_id)
        if activity:
            await self.db.delete(activity)
            await self.db.commit()
            return True
        return False

    async def delete_user_activities(self, user_id: str) -> int:
        """
        Delete all activities for a specific user.

        Parameters
        ----------
        user_id : str
            The ID of the user

        Returns
        -------
        int
            Number of deleted records
        """
        stmt = delete(UserActivity).where(UserActivity.user_id == user_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def search_activities_by_description(self, search_term: str, skip: int = 0, limit: int = 100) -> List[UserActivity]:
        """
        Search activities by description keyword.

        Parameters
        ----------
        search_term : str
            Term to search within activity descriptions
        skip : int
            Number of records to skip (pagination)
        limit : int
            Maximum number of records to return

        Returns
        -------
        List[UserActivity]
            List of activities matching the description search
        """
        stmt = (
            select(UserActivity)
            .where(UserActivity.description.ilike(f"%{search_term}%"))
            .order_by(UserActivity.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
