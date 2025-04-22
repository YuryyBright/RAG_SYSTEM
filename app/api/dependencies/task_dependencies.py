from infrastructure.repositories.repository.task_repository import TaskRepository
from infrastructure.repositories.repository import get_async_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_task_repository(db: AsyncSession = Depends(get_async_db)) -> TaskRepository:
    """
    Get task repository instance.
    """
    return TaskRepository(db)
