from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import enum


class TaskStatusEnum(str, enum.Enum):
    """
    Enumeration of possible statuses a task can have throughout its lifecycle.
    Represents the operational state of a task.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskTypeEnum(str, enum.Enum):
    """
    Enumeration of various types of tasks the system can handle.
    Defines the nature or category of the task being performed.
    """
    THEME_PROCESSING = "theme_processing"
    DOCUMENT_PROCESSING = "document_processing"
    EMBEDDING_GENERATION = "embedding_generation"
    FILE_DOWNLOAD = "file_download"
    FILE_READING = "file_reading"
    TEXT_CHUNKING = "text_chunking"
    VECTOR_STORAGE = "vector_storage"


class StepStatus(BaseModel):
    """
    Represents the current status of an individual processing step
    in a task pipeline.
    """
    name: str
    status: TaskStatusEnum
    progress: float = 0.0


class LogEntry(BaseModel):
    """
    A log entry for task tracking and debugging, containing a
    timestamp and a human-readable message.
    """
    timestamp: str
    message: str


class TaskCreate(BaseModel):
    """
    Schema to define the structure of a task creation request.
    Used when a client initiates a new task.
    """
    task_type: TaskTypeEnum
    theme_id: Optional[str] = None
    description: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None


class TaskUpdate(BaseModel):
    """
    Schema to define updates to a task during its lifecycle.
    Used for patching the task's status or progress.
    """
    status: Optional[TaskStatusEnum] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None


class TaskResponse(BaseModel):
    """
    Schema for the summarized view of a task, typically returned in list APIs.
    """
    id: str
    type: TaskTypeEnum
    user_id: str
    theme_id: Optional[str] = None
    description: str
    status: TaskStatusEnum
    progress: float
    created_at: Union[datetime, str]
    started_at: Optional[Union[datetime, str]] = None
    completed_at: Optional[Union[datetime, str]] = None
    error_message: Optional[str] = None



class TaskDetailResponse(TaskResponse):
    """
    Schema providing full task details including metadata,
    logs, and step-specific progress.
    """
    logs: List[LogEntry] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)
    steps: List[Dict[str, Any]] = []
    current_step: int = 0




class CreateTaskRequest(BaseModel):
    """
    Request schema for initiating a task, providing type,
    optional step, and metadata.
    """
    type: str = Field(..., )
    theme_id: Optional[str] = Field(None,)
    description: Optional[str] = Field(None)
    step: Optional[str] = Field(None,)
    files: Optional[List[str]] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class TaskLogEntry(BaseModel):
    """
    Request schema for appending a log entry to an existing task.
    """
    log_entry: str
