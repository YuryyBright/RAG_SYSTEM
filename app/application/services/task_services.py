# app/core/services/task_manager.py
import json
import logging
from datetime import datetime
from typing import Callable, Any, Optional, List, Dict

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.task import TaskTypeEnum, TaskStatusEnum
from infrastructure.repositories.repository.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class Task:
    """
    Domain-level Task entity to track background tasks.
    """

    def __init__(
        self,
        task_type: TaskTypeEnum,
        user_id: str,
        theme_id: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        # Add an ID field that will be None until persisted in DB.
        self.id: Optional[str] = None

        self.type = task_type
        self.user_id = user_id
        self.theme_id = theme_id
        self.description = description
        self.status = TaskStatusEnum.PENDING
        self.progress = 0.0  # 0 to 100
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.logs: List[Dict[str, str]] = []
        self.metadata = metadata or {}
        self.steps: List[Dict[str, Any]] = []
        self.current_step = 0

    def start(self):
        """
        Mark task as started.
        """
        self.status = TaskStatusEnum.IN_PROGRESS
        self.started_at = datetime.now()
        self.add_log(f"Task {self.id} started")

    def complete(self):
        """
        Mark task as completed.
        """
        self.status = TaskStatusEnum.COMPLETED
        self.progress = 100.0
        self.completed_at = datetime.now()
        self.add_log(f"Task {self.id} completed")

    def fail(self, error_message: str):
        """
        Mark task as failed.
        """
        self.status = TaskStatusEnum.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()
        self.add_log(f"Task {self.id} failed: {error_message}")

    def cancel(self):
        """
        Mark task as cancelled.
        """
        self.status = TaskStatusEnum.CANCELLED
        self.completed_at = datetime.now()
        self.add_log(f"Task {self.id} cancelled")

    def update_progress(self, progress: float, message: Optional[str] = None):
        """
        Update progress percentage and optionally log a message.
        """
        self.progress = min(max(progress, 0.0), 100.0)
        if message:
            self.add_log(message)

    def add_log(self, message: str):
        """
        Add a log message with timestamp.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append({"timestamp": timestamp, "message": message})

    def set_steps(self, steps: List[str]):
        """
        Set the steps for this task.
        """
        self.steps = [
            {"name": step, "status": TaskStatusEnum.PENDING, "progress": 0.0}
            for step in steps
        ]

    def update_step(
        self,
        step_index: int,
        status: TaskStatusEnum,
        progress: float = None,
        message: Optional[str] = None
    ):
        """
        Update the status and progress of a specific step.
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = status
            if progress is not None:
                self.steps[step_index]["progress"] = progress
            if message:
                self.add_log(f"Step {self.steps[step_index]['name']}: {message}")

    def advance_step(self):
        """
        Advance to the next step, marking the old one as complete.
        """
        if self.current_step < len(self.steps) - 1:
            if self.current_step >= 0:
                self.update_step(self.current_step, TaskStatusEnum.COMPLETED, 100.0)
            self.current_step += 1
            self.update_step(self.current_step, TaskStatusEnum.IN_PROGRESS, 0.0)
            self.add_log(f"Advanced to step: {self.steps[self.current_step]['name']}")
            if self.steps:
                # Overall progress based on how many steps are completed
                self.progress = (self.current_step * 100.0) / len(self.steps)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary for API responses or debugging.
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "user_id": self.user_id,
            "theme_id": self.theme_id,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "logs": self.logs,
            "metadata": self.metadata,
            "steps": self.steps,
            "current_step": self.current_step
        }


class TaskManager:
    """
    A database-backed Task Manager that creates and manages Tasks using TaskRepository.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the TaskManager with a database session.
        """
        self.db_session = db_session
        self.repository = TaskRepository(db_session)

    async def create_task(
        self,
        task_type: TaskTypeEnum,
        user_id: str,
        theme_id: Optional[str] = None,
        description: str = "",
        metadata: Optional[dict] = None
    ) -> Task:
        """
        Create a new Task and store it in the database.
        """
        task = Task(
            task_type=task_type,
            user_id=user_id,
            theme_id=theme_id,
            description=description,
            metadata=metadata or {}
        )
        created_model = await self.repository.create(task)
        task.id = created_model.id  # DB-generated ID
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by ID from the database.
        """
        db_model = await self.repository.get_by_id(task_id)
        if not db_model:
            return None

        domain_task = Task(
            task_type=TaskTypeEnum(db_model.task_type),
            user_id=db_model.user_id,
            theme_id=db_model.theme_id,
            description=db_model.description,
            metadata=json.loads(db_model.task_metadata or '{}')
        )
        domain_task.id = db_model.id
        domain_task.status = TaskStatusEnum(db_model.status)
        domain_task.progress = db_model.progress
        domain_task.created_at = db_model.created_at
        domain_task.started_at = db_model.started_at
        domain_task.completed_at = db_model.completed_at
        domain_task.error_message = db_model.error_message
        domain_task.logs = json.loads(db_model.logs or '[]')  # ✅ fixed
        domain_task.steps = json.loads(db_model.steps or '[]')  # ✅ fixed
        domain_task.current_step = db_model.current_step
        return domain_task

    async def get_user_tasks(self, user_id: str) -> List[Task]:
        """
        Get all tasks for a specific user from the database.
        """
        db_tasks = await self.repository.get_by_user(user_id)
        return [self._to_domain_task(db_task) for db_task in db_tasks]

    async def get_theme_tasks(self, theme_id: str) -> List[Task]:
        """
        Get all tasks for a given theme ID from the database.
        """
        db_tasks = await self.repository.get_by_theme(theme_id)
        return [self._to_domain_task(db_task) for db_task in db_tasks]

    async def update_task_status(
        self,
        task_id: str,
        status: Optional[str] = None,
        current_step: Optional[int] = None,
        progress: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update the status, progress, current step, or error message of a task.

        Args:
            task_id (str): ID of the task to update.
            status (Optional[str]): New status for the task (pending, in_progress, completed, failed, etc.).
            current_step (Optional[int]): Current processing step index.
            progress (Optional[float]): Progress percentage (0.0 - 100.0).
            error_message (Optional[str]): Error message if task failed.

        Returns:
            bool: True if the update succeeded, False otherwise.
        """
        # Fetch task first
        task = await self.get_task(task_id)
        if not task:
            return False

        # Apply updates
        if status:
            task.status = TaskStatusEnum(status)
        if progress is not None:
            task.progress = min(max(progress, 0.0), 100.0)
        if current_step is not None:
            task.current_step = current_step
        if error_message:
            task.error_message = error_message
            task.add_log(f"Error occurred: {error_message}")
            task.completed_at = datetime.now()

        # Persist to DB
        success = await self.repository.update(
            task_id=task.id,
            status=task.status.value,
            progress=task.progress,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            logs=task.logs,
            task_metadata=task.metadata,
            steps=task.steps,
            current_step=task.current_step
        )
        return success
    async def run_task_async(
        self,
        task: Task,
        coroutine_func: Callable[..., Any],
        *args,
        **kwargs
    ) -> None:
        """
        Run a task asynchronously. If it fails, mark as failed; otherwise mark as completed.
        """
        # Mark as started in domain object
        task.start()
        await self.repository.update(task)

        try:
            await coroutine_func(task, *args, **kwargs)
            task.complete()
            await self.repository.update(task)
        except Exception as e:
            logger.exception(f"Task {task.id} failed with error: {str(e)}")
            task.fail(str(e))
            await self.repository.update(task)

    def run_task_in_background(
        self,
        background_tasks: BackgroundTasks,
        task: Task,
        coroutine_func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Task:
        """
        Schedule a task to run in the background using FastAPI's BackgroundTasks.
        """
        background_tasks.add_task(self.run_task_async, task, coroutine_func, *args, **kwargs)
        return task

    async def cancel_task(self, task_id: str) -> bool:
        """
        Mark a task as cancelled, if still pending or in progress.
        """
        task = await self.get_task(task_id)
        if not task:
            return False
        if task.status in (TaskStatusEnum.PENDING, TaskStatusEnum.IN_PROGRESS):
            task.cancel()
            await self.repository.update(task)
            return True
        return False

    def _to_domain_task(self, db_model) -> Task:
        """
        Helper to convert a DB task model to our domain Task object.
        """
        domain_task = Task(
            task_type=TaskTypeEnum(db_model.task_type),
            user_id=db_model.user_id,
            theme_id=db_model.theme_id,
            description=db_model.description,
            metadata=json.loads(db_model.task_metadata or '{}')  # fix here
        )
        domain_task.id = db_model.id
        domain_task.status = TaskStatusEnum(db_model.status)
        domain_task.progress = db_model.progress
        domain_task.created_at = db_model.created_at
        domain_task.started_at = db_model.started_at
        domain_task.completed_at = db_model.completed_at
        domain_task.error_message = db_model.error_message
        domain_task.logs = json.loads(db_model.logs or '[]')  # fix here
        domain_task.steps = json.loads(db_model.steps or '[]')  # fix here
        domain_task.current_step = db_model.current_step
        return domain_task
