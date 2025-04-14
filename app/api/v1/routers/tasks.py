"""
API routes for task management related to vector database creation.

This module defines endpoints for creating tasks, retrieving tasks,
cancelling tasks, and adding log entries to tasks. These tasks are
processed in the background and tracked in the database.
"""

import uuid
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks
)
from sqlalchemy.ext.asyncio import AsyncSession

# Schemas for creating and updating tasks/logs
from api.schemas.task import (
    CreateTaskRequest,
    TaskLogEntry,
    TaskTypeEnum,
    TaskStatusEnum,
    TaskResponse
)

# Repository for Task objects
from app.infrastructure.database.repository.task_repository import TaskRepository

# Example dependencies for injecting DB sessions, repositories, etc.
from app.api.dependencies import (
    get_task_repository,
    get_async_db,
    get_theme_use_case,
    # get_processing_service    # If your system uses a separate processing service
)

# A logger utility for debugging
from app.utils.logger_util import get_logger
from core.services.task_services import Task

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    task_repository: TaskRepository = Depends(get_task_repository),
    theme_use_case=Depends(get_theme_use_case),
    # processing_service: ProcessingService = Depends(get_processing_service),
):
    """
    Create a new processing task and, if applicable, start it in the background.

    This endpoint:
      1. Validates the task type and (optionally) the theme ID.
      2. Creates a domain-level Task object.
      3. Persists the Task to the database via TaskRepository.
      4. Optionally schedules background work if a recognized step is provided.

    Parameters
    ----------
    request : CreateTaskRequest
        The request body for creating a task, including the task type, theme_id, step, etc.
    background_tasks : BackgroundTasks
        FastAPI's background task manager, used to schedule processing asynchronously.
    db : AsyncSession
        SQLAlchemy AsyncSession for database access.
    task_repository : TaskRepository
        Repository for Task-related database operations.
    theme_use_case : ThemeUseCase
        Example use-case class for validating themes (if theme IDs need to exist).
    # processing_service : ProcessingService
    #     A service that actually handles downloading, reading, embedding, etc.

    Returns
    -------
    Task
        The created domain-level Task object. Its `id` is assigned after DB persistence.
    """
    # 1. Validate the task type
    try:
        task_type = TaskTypeEnum(request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {request.type}")

    # 2. If a theme_id is provided, ensure the theme actually exists
    if request.theme_id:
        existing_theme = await theme_use_case.get_theme(request.theme_id)
        if not existing_theme:
            raise HTTPException(status_code=404, detail="Specified theme does not exist.")

    # 3. Create a domain-level Task
    domain_task = Task(
        task_type=task_type,
        user_id="current_user_id",  # Replace with real user ID from your auth system
        theme_id=request.theme_id,
        description=request.description or f"Processing theme {request.theme_id}",
        metadata={
            "step": request.step,
            "files": request.files,
            **request.metadata
        },
    )

    # For demonstration: use a simple numeric step system
    if request.step == "download":
        domain_task.current_step = 0
    elif request.step == "read":
        domain_task.current_step = 1
    elif request.step == "embed":
        domain_task.current_step = 2
    # ... handle additional steps if needed

    # 4. Persist the task in DB
    db_task_model = await task_repository.create(domain_task)
    domain_task.id = db_task_model.id

    # 5. Optionally schedule background work based on the step
    # if request.step == "download":
    #     background_tasks.add_task(
    #         processing_service.process_downloads,
    #         task_id=domain_task.id,
    #         file_ids=request.files
    #     )
    # elif request.step == "read":
    #     background_tasks.add_task(
    #         processing_service.process_text_extraction,
    #         task_id=domain_task.id,
    #         file_ids=request.files
    #     )
    # elif request.step == "embed":
    #     background_tasks.add_task(
    #         processing_service.process_embeddings,
    #         task_id=domain_task.id,
    #         file_ids=request.files
    #     )
    # else:
    #     logger.warning(f"No specific process defined for step '{request.step}'")

    return domain_task


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    user_id: Optional[str] = None,
    theme_id: Optional[str] = None,
    status: Optional[str] = None,
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Retrieve tasks based on optional filter criteria (user_id, theme_id, status).

    Parameters
    ----------
    user_id : str, optional
        If provided, filter tasks by this user ID.
    theme_id : str, optional
        If provided, filter tasks by this theme ID.
    status : str, optional
        If provided, filter tasks by this status (pending, in_progress, etc.).
    task_repository : TaskRepository
        Repository for Task-related DB operations.

    Returns
    -------
    List[Task]
        A list of domain-level Task objects that match the filters.
    """
    tasks: List[Task] = []

    # Filter by theme_id
    if theme_id:
        db_tasks = await task_repository.get_by_theme(theme_id)
        tasks = [await _to_domain_task(db_task) for db_task in db_tasks]

    # Filter by user_id (only if theme_id not used)
    elif user_id:
        db_tasks = await task_repository.get_by_user(user_id)
        tasks = [await _to_domain_task(db_task) for db_task in db_tasks]

    # If no filters are provided, return an empty list or some default behavior
    else:
        return []

    # If a status filter is specified, narrow it down further
    if status:
        try:
            valid_status = TaskStatusEnum(status)
            tasks = [t for t in tasks if t.status == valid_status]
        except ValueError:
            # If the user supplied a status that doesn't match our enum, return empty
            tasks = []

    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Retrieve a single task by its unique ID.

    Parameters
    ----------
    task_id : str
        The ID of the task to retrieve.
    task_repository : TaskRepository
        Repository for Task-related DB operations.

    Raises
    ------
    HTTPException
        If the task does not exist (404).

    Returns
    -------
    Task
        The requested domain-level Task object.
    """
    db_task = await task_repository.get_by_id(task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    return await _to_domain_task(db_task)


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    task_repository: TaskRepository = Depends(get_task_repository),
    # processing_service: ProcessingService = Depends(get_processing_service),
):
    """
    Cancel a running or pending task.

    Parameters
    ----------
    task_id : str
        The ID of the task to cancel.
    task_repository : TaskRepository
        Repository for Task-related DB operations.
    # processing_service : ProcessingService
    #     Service for cancelling tasks that may be running asynchronously.

    Raises
    ------
    HTTPException
        If the task does not exist, or if its status is not cancellable.

    Returns
    -------
    dict
        A JSON response indicating the result of the cancellation.
    """
    db_task = await task_repository.get_by_id(task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Only PENDING or IN_PROGRESS tasks can be cancelled
    cancellable_statuses = (TaskStatusEnum.PENDING.value, TaskStatusEnum.IN_PROGRESS.value)
    if db_task.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status {db_task.status}"
        )

    # If you have a background worker system, you could signal that system here:
    # await processing_service.cancel_task(task_id)

    # Convert to domain, cancel it, then save
    domain_task = await _to_domain_task(db_task)
    domain_task.cancel()
    await task_repository.update(domain_task)

    return {"status": "success", "message": f"Task {task_id} has been cancelled"}


@router.post("/{task_id}/logs")
async def add_task_log(
    task_id: str,
    log_entry: TaskLogEntry,
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Append a log entry to the specified Task.

    Parameters
    ----------
    task_id : str
        The ID of the task to log to.
    log_entry : TaskLogEntry
        A simple schema containing the new log message.
    task_repository : TaskRepository
        Repository for Task-related DB operations.

    Raises
    ------
    HTTPException
        If the task is not found.

    Returns
    -------
    dict
        A confirmation message indicating the log entry was added.
    """
    db_task = await task_repository.get_by_id(task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    domain_task = await _to_domain_task(db_task)

    # Here we use a random ID as a timestamp for demonstration only.
    # Normally, you'd add a real datetime string:
    domain_task.logs.append({
        "timestamp": str(uuid.uuid4()),
        "message": log_entry.log_entry
    })

    await task_repository.update(domain_task)
    return {"status": "success", "message": "Log entry added"}


async def _to_domain_task(db_task_model) -> Task:
    """
    Convert a database model into a domain-level Task object.

    Parameters
    ----------
    db_task_model : ProcessingTask
        The ORM model from the database.

    Returns
    -------
    Task
        A domain-level Task object with matching fields.
    """
    domain_task = Task(
        task_type=TaskTypeEnum(db_task_model.task_type),
        user_id=db_task_model.user_id,
        theme_id=db_task_model.theme_id,
        description=db_task_model.description,
        metadata=db_task_model.parsed_metadata,  # e.g. JSON-loaded object
    )
    # Populate database-assigned fields
    domain_task.id = db_task_model.id
    domain_task.status = TaskStatusEnum(db_task_model.status)
    domain_task.progress = db_task_model.progress
    domain_task.created_at = db_task_model.created_at
    domain_task.started_at = db_task_model.started_at
    domain_task.completed_at = db_task_model.completed_at
    domain_task.error_message = db_task_model.error_message
    domain_task.logs = db_task_model.parsed_logs    # e.g. JSON-loaded logs
    domain_task.steps = db_task_model.parsed_steps  # e.g. JSON-loaded steps
    domain_task.current_step = db_task_model.current_step

    return domain_task
