from typing import Optional, List, Dict, Any
import json

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.db_models import ProcessingTask
from app.utils.logger_util import get_logger
logger = get_logger(__name__)


class TaskRepository:
    """
    Repository class for managing processing task-related database operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the TaskRepository with a database session.
        """
        self.db = db

    async def get_by_id(self, task_id: str) -> Optional[ProcessingTask]:
        """
        Retrieve a task by its unique ID.
        """
        result = await self.db.execute(
            select(ProcessingTask).where(ProcessingTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> List[ProcessingTask]:
        """
        Retrieve all tasks created by a specific user.
        """
        result = await self.db.execute(
            select(ProcessingTask).where(ProcessingTask.user_id == user_id)
        )
        return result.scalars().all()

    async def get_by_theme(self, theme_id: str) -> List[ProcessingTask]:
        """
        Retrieve all tasks associated with a specific theme.
        """
        result = await self.db.execute(
            select(ProcessingTask).where(ProcessingTask.theme_id == theme_id)
        )
        return result.scalars().all()

    async def create(
        self,
        task
    ) -> ProcessingTask:
        """
        Create a new processing task record in the database, using raw data
        rather than a domain `Task` object.
        """
        db_task = ProcessingTask(
            task_type=task.type.value,
            user_id=task.user_id,
            theme_id=task.theme_id,
            description=task.description,
            status=task.status.value,
            progress=task.progress,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            logs=json.dumps(task.logs),
            task_metadata=json.dumps(task.metadata),
            steps=json.dumps(task.steps),
            current_step=task.current_step
        )
        self.db.add(db_task)
        await self.db.commit()
        await self.db.refresh(db_task)
        return db_task

    async def update(
        self,
        *,
        task_id: str,
        status: str,
        progress: float,
        started_at,
        completed_at,
        error_message: Optional[str],
        logs: List[Dict[str, Any]],
        task_metadata: Dict[str, Any],
        steps: List[Dict[str, Any]],
        current_step: int
    ) -> bool:
        """
        Update an existing task record in the DB by passing raw fields (no domain object).
        """
        stmt = (
            update(ProcessingTask)
            .where(ProcessingTask.id == task_id)
            .values(
                status=status,
                progress=progress,
                started_at=started_at,
                completed_at=completed_at,
                error_message=error_message,
                logs=json.dumps(logs),
                task_metadata=json.dumps(task_metadata),
                steps=json.dumps(steps),
                current_step=current_step,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task record by its ID from the DB.
        """
        result = await self.db.execute(
            delete(ProcessingTask).where(ProcessingTask.id == task_id)
        )
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Deleted task: {task_id}")
        else:
            logger.warning(f"Task delete failed (not found): {task_id}")

        return result.rowcount > 0
