from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import and_

from app.infrastructure.database.db_models import Session  # You'll need to create this model
from utils.logger_util import get_logger

logger = get_logger(__name__)
class SessionRepository:
    """
    Repository for managing user sessions in the database.

    This class handles all database operations related to user sessions,
    including creating, retrieving, updating, and deleting sessions.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the SessionRepository with a database session.

        Parameters
        ----------
        db : AsyncSession
            The database session to use for queries.
        """
        self.db = db

    async def create_session(
            self,
            session_id: str,
            user_id: str,
            username: str,
            expires_at: datetime,
            csrf_token: str,
            remember: bool = False
    ) -> bool:
        """
        Create a new session in the database.

        Parameters
        ----------
        session_id : str
            The unique session identifier.
        user_id : str
            The ID of the user associated with the session.
        username : str
            The username of the user.
        expires_at : datetime
            When the session expires.
        csrf_token : str
            The CSRF token associated with this session.
        remember : bool, optional
            Whether this is a long-lived "remember me" session.

        Returns
        -------
        bool
            True if the session was created successfully, False otherwise.
        """
        try:
            # Create new session object
            new_session = Session(
                id=session_id,
                user_id=user_id,
                username=username,
                expires_at=expires_at,
                csrf_token=csrf_token,
                remember=remember,
                created_at=datetime.utcnow(),
                user_agent=None,  # This could be added if you track user agents
                ip_address=None,  # This could be added for IP tracking
            )

            # Add to database
            self.db.add(new_session)
            await self.db.commit()

            logger.info(f"Session created for user: {username}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating session: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by its ID.

        Parameters
        ----------
        session_id : str
            The session ID to look up.

        Returns
        -------
        Dict[str, Any] or None
            The session data if found, otherwise None.
        """
        try:
            # Query for session
            stmt = select(Session).where(Session.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if not session:
                return None

            # Convert to dictionary
            return {
                "id": session.id,
                "user_id": session.user_id,
                "username": session.username,
                "expires_at": session.expires_at,
                "csrf_token": session.csrf_token,
                "remember": session.remember,
                "created_at": session.created_at,
                "last_accessed": session.last_accessed if hasattr(session, "last_accessed") else None,
            }
        except Exception as e:
            logger.error(f"Error retrieving session: {e}")
            return None

    async def update_session_access_time(self, session_id: str) -> bool:
        """
        Update the last accessed time for a session.

        Parameters
        ----------
        session_id : str
            The session ID to update.

        Returns
        -------
        bool
            True if the session was updated successfully, False otherwise.
        """
        try:
            # Query for session
            stmt = select(Session).where(Session.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if not session:
                logger.warning(f"Session not found for update: {session_id[:8]}...")
                return False

            # Update last accessed time
            session.last_accessed = datetime.utcnow()
            await self.db.commit()

            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating session access time: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from the database.

        Parameters
        ----------
        session_id : str
            The session ID to delete.

        Returns
        -------
        bool
            True if the session was deleted successfully, False otherwise.
        """
        try:
            # Delete session
            stmt = delete(Session).where(Session.id == session_id)
            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"Session deleted: {session_id[:8]}...")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting session: {e}")
            return False

    async def delete_user_sessions(self, user_id: str) -> bool:
        """
        Delete all sessions for a specific user.

        Parameters
        ----------
        user_id : str
            The ID of the user.

        Returns
        -------
        bool
            True if the sessions were deleted successfully, False otherwise.
        """
        try:
            # Delete user sessions
            stmt = delete(Session).where(Session.user_id == user_id)
            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"All sessions deleted for user: {user_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user sessions: {e}")
            return False

    async def clear_expired_sessions(self) -> int:
        """
        Delete all expired sessions from the database.

        Returns
        -------
        int
            The number of sessions deleted.
        """
        try:
            # Delete expired sessions
            now = datetime.utcnow()
            stmt = delete(Session).where(Session.expires_at < now)
            result = await self.db.execute(stmt)
            await self.db.commit()

            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Cleared {deleted_count} expired sessions")

            return deleted_count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error clearing expired sessions: {e}")
            return 0

    async def get_active_sessions_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user.

        Parameters
        ----------
        user_id : str
            The ID of the user.

        Returns
        -------
        List[Dict[str, Any]]
            List of active sessions for the user.
        """
        try:
            # Query for active sessions
            now = datetime.utcnow()
            stmt = select(Session).where(
                and_(
                    Session.user_id == user_id,
                    Session.expires_at > now
                )
            )
            result = await self.db.execute(stmt)
            sessions = result.scalars().all()

            # Convert to list of dictionaries
            return [
                {
                    "id": session.id,
                    "user_id": session.user_id,
                    "username": session.username,
                    "expires_at": session.expires_at,
                    "created_at": session.created_at,
                    "last_accessed": session.last_accessed if hasattr(session, "last_accessed") else None,
                    "user_agent": session.user_agent if hasattr(session, "user_agent") else None,
                    "ip_address": session.ip_address if hasattr(session, "ip_address") else None,
                }
                for session in sessions
            ]
        except Exception as e:
            logger.error(f"Error retrieving user sessions: {e}")
            return []
