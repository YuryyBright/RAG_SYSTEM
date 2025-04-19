from infrastructure.database.repository.task_repository import TaskRepository
from app.infrastructure.database.repository import get_async_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_task_repository(db: AsyncSession = Depends(get_async_db)) -> TaskRepository:
    """
    Get task repository instance.
    """
    return TaskRepository(db)
