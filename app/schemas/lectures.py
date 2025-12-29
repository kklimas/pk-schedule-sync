from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class LectureSyncInfo(BaseModel):
    job_id: str
    status: str
    date: Optional[datetime] = None

class LectureResponse(BaseModel):
    id: int
    date: str
    start_time: str
    end_time: str
    summary: str
    subject: Optional[str] = None
    type: Optional[str] = None
    teacher: Optional[str] = None
    room: Optional[str] = None
    last_sync: Optional[LectureSyncInfo] = None



class LectureListResponse(BaseModel):
    items: list[LectureResponse]
    total: int
    page: int
    size: int
