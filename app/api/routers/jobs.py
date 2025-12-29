from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.services.job_service import job_service
from app.schemas.jobs import JobStatusResponse, JobListResponse
from app.database import get_db

router = APIRouter()

@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves a paged list of jobs ordered by completion date."""
    skip = (page - 1) * size
    items, total = job_service.get_jobs(db, skip=skip, limit=size)
    
    return JobListResponse(
        items=[
            JobStatusResponse(
                job_id=item.id,
                status=item.status,
                started_at=item.started_at,
                completed_at=item.completed_at,
                message=item.message,
                sheet_url=item.sheet_url,
                triggered_by=item.triggered_by
            ) for item in items
        ],
        total=total,
        page=page,
        size=size
    )

@router.post("/", response_model=JobStatusResponse)

async def trigger_sync(db: Session = Depends(get_db)):
    """Triggers the PK schedule synchronization job."""
    job = await job_service.execute_sync(db, triggered_by="user")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        started_at=job.started_at,
        message=job.message,
        triggered_by=job.triggered_by
    )

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str, db: Session = Depends(get_db)):
    """Retrieves the status of a specific synchronization job."""
    job = job_service.get_job_status(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        message=job.message,
        triggered_by=job.triggered_by
    )
