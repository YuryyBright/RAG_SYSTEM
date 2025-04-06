from datetime import datetime
from pydantic import BaseModel


class FileResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    is_public: bool
    created_at: datetime

    class Config:
        orm_mode = True