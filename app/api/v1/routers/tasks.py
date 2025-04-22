"""
API routes for task management related to vector database creation.

This module defines endpoints for creating tasks, retrieving tasks,
cancelling tasks, and adding log entries to tasks. These tasks are
processed in the background and tracked in the database.
"""

from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware_auth import get_current_active_user
# Schemas for creating and updating tasks/logs
from api.schemas.task import (
    CreateTaskRequest,
    TaskLogEntry,
    TaskTypeEnum,
    TaskStatusEnum,
    TaskResponse
)

# Repository for Task objects
from infrastructure.repositories.repository.task_repository import TaskRepository
from api.dependencies.task_dependencies import get_task_repository
# Example dependencies for injecting DB sessions, repositories, etc.
from app.api.dependencies.dependencies import (
    get_async_db,
    get_theme_use_case,
    # get_processing_service    # If your system uses a separate processing service
)

# A logger utility for debugging
from app.utils.logger_util import get_logger
from application.services.task_services import TaskManager

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    user: dict = Depends(get_current_active_user),
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

    # Create metadata with proper null handling
    metadata = {
        "step": request.step,
        "files": request.files
    }
    if request.metadata:
        metadata.update(request.metadata)

    # 3. Create task using the TaskManager
    task_manager = TaskManager(db)
    domain_task = await task_manager.create_task(
        task_type=task_type,
        user_id=user.id,
        theme_id=request.theme_id,
        description=request.description or f"Processing theme {request.theme_id}",
        metadata=metadata
    )

    # 4. Set the current step based on step name
    step_mapping = {
        "download": 0,
        "read": 1,
        "embed": 2
    }

    if request.step in step_mapping:
        domain_task.current_step = step_mapping[request.step]
        # Update task with new step
        await task_repository.update(
            task_id=domain_task.id,
            status=domain_task.status.value,
            progress=domain_task.progress,
            started_at=domain_task.started_at,
            completed_at=domain_task.completed_at,
            error_message=domain_task.error_message,
            logs=domain_task.logs,
            task_metadata=domain_task.metadata,
            steps=domain_task.steps,
            current_step=domain_task.current_step,
        )

    # 5. Optionally schedule background work based on the step
    # if request.step in step_mapping and processing_service:
    #     task_manager.run_task_in_background(
    #         background_tasks,
    #         domain_task,
    #         processing_service.process_step,
    #         step=request.step,
    #         file_ids=request.files
    #     )

    return domain_task


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    user_id: Optional[str] = None,
    theme_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve tasks based on optional filter criteria (user_id, theme_id, status).
    """
    task_manager = TaskManager(db)
    tasks = []

    # Filter tasks by criteria
    if theme_id:
        tasks = await task_manager.get_theme_tasks(theme_id)
    elif user_id:
        tasks = await task_manager.get_user_tasks(user_id)
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
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a single task by its unique ID.
    """
    task_manager = TaskManager(db)
    task = await task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.post("/{task_id}/resume")
async def resume_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    task_repository: TaskRepository = Depends(get_task_repository),
):
    """
    Resume a paused task and mark it as in_progress again.
    """
    task_manager = TaskManager(db)
    task = await task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatusEnum.PAUSED:
        raise HTTPException(status_code=400, detail="Only paused tasks can be resumed")

    task.status = TaskStatusEnum.IN_PROGRESS
    task.add_log("Task resumed")

    await task_repository.update(
        task_id=task.id,
        status=task.status.value,
        progress=task.progress,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        logs=task.logs,
        task_metadata=task.metadata,
        steps=task.steps,
        current_step=task.current_step,
    )

    return {"status": "success", "message": f"Task {task_id} resumed"}


@router.post("/embed-step", response_model=dict)
async def start_embed_step(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    task_repository: TaskRepository = Depends(get_task_repository),
    # processing_service = Depends(get_processing_service),
):
    """
    Start the embedding step for a task.
    """
    task_manager = TaskManager(db)
    task = await task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.current_step = 2  # 2 = embed
    task.status = TaskStatusEnum.IN_PROGRESS
    task.add_log("Starting embedding process")

    await task_repository.update(
        task_id=task.id,
        status=task.status.value,
        progress=task.progress,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        logs=task.logs,
        task_metadata=task.metadata,
        steps=task.steps,
        current_step=task.current_step,
    )

    # Schedule background task for embedding
    # if processing_service:
    #     task_manager.run_task_in_background(
    #         background_tasks,
    #         task,
    #         processing_service.process_embeddings,
    #         task_id=task_id
    #     )

    return {"status": "success", "message": "Embedding process started."}


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Cancel a running or pending task.
    """
    task_manager = TaskManager(db)
    success = await task_manager.cancel_task(task_id)

    if not success:
        # Get the task to determine why cancellation failed
        task = await task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task with status {task.status.value}"
            )

    return {"status": "success", "message": f"Task {task_id} has been cancelled"}


@router.post("/{task_id}/logs")
async def add_task_log(
    task_id: str,
    log_entry: TaskLogEntry,
    db: AsyncSession = Depends(get_async_db),
    task_repository: TaskRepository = Depends(get_task_repository),
):
    """
    Append a log entry to the specified Task.
    """
    task_manager = TaskManager(db)
    task = await task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.add_log(log_entry.log_entry)

    await task_repository.update(
        task_id=task.id,
        status=task.status.value,
        progress=task.progress,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_message=task.error_message,
        logs=task.logs,
        task_metadata=task.metadata,
        steps=task.steps,
        current_step=task.current_step,
    )

    return {"status": "success", "message": "Log entry added"}