from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    message: Optional[str] = None
    sheet_url: Optional[str] = None
    triggered_by: Optional[str] = "system"

class JobListResponse(BaseModel):
    items: list[JobStatusResponse]
    total: int
    page: int
    size: int

