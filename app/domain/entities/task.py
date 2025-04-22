# domain/entities/task.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from api.schemas.task import TaskTypeEnum, TaskStatusEnum


@dataclass
class Task:
    id: Optional[str]
    type: TaskTypeEnum
    user_id: str
    theme_id: Optional[str] = None
    description: str = ""
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    logs: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0