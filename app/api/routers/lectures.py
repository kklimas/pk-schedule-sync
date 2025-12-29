from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.lecture_service import lecture_service
from app.schemas.lectures import LectureListResponse, LectureResponse, LectureSyncInfo

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=LectureListResponse)
def get_lectures(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * size
    items, total = lecture_service.get_lectures(db, skip=skip, limit=size)
    
    return LectureListResponse(
        items=[
            LectureResponse(
                id=item.id,
                date=item.date,
                start_time=item.start_time,
                end_time=item.end_time,
                summary=item.summary,
                subject=item.subject,
                type=item.type,
                teacher=item.teacher,
                room=item.room,
                last_sync=LectureSyncInfo(
                    job_id=item.last_sync.id,
                    status=item.last_sync.status,
                    date=item.last_sync.completed_at
                ) if item.last_sync else None


            ) for item in items
        ],
        total=total,
        page=page,
        size=size
    )
