import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.jobs import Job
from app.database import SessionLocal
from app.jobs.sync_job import run_sync_job
from app.services.slack_service import slack_service

class JobService:
    async def execute_sync(self, db: Session, triggered_by: str = "system"):
        new_job = Job(
            status="running",
            started_at=datetime.utcnow(),
            message="Initialising sync job...",
            triggered_by=triggered_by
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        
        job_id = new_job.id
        
        # Send Slack notification to Status Channel
        slack_service.send_job_status(
            title="🔄 Sync Job Started",
            status="Running",
            message=f"Job ID: {job_id}\nTriggered by: {triggered_by}"
        )
        
        # Simulate long running task in background
        asyncio.create_task(self._run_job(job_id))
        
        return new_job

    async def _run_job(self, job_id: str):
        db = SessionLocal()
        try:
            # Execute the actual sync job logic
            result_data = await run_sync_job(job_id)
            
            result_msg = result_data.get("message", "Sync completed.")
            added = result_data.get("added", [])
            updated = result_data.get("updated", [])
            deleted = result_data.get("deleted", [])
            sheet_url = result_data.get("sheet_url")
    
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.message = result_msg
                db.commit()

                # Send Slack notification to Status Channel
                slack_service.send_job_status(
                    title="✅ Sync Job Completed",
                    status="Completed",
                    message=f"Job ID: {job_id}\n{result_msg}"
                )

                # Send detailed notice if anything changed
                if added or updated or deleted:
                    slack_service.send_schedule_update(
                        title="📅 Schedule Changes Detected",
                        message=f"Sync finished. See what changed below:",
                        added=added,
                        updated=updated,
                        deleted=deleted,
                        sheet_url=sheet_url
                    )
                    
                    # Sync with Google Calendar (wrapped in try-except to not break the flow)
                    try:
                        from app.services.google_calendar_service import google_calendar_service
                        google_calendar_service.batch_sync_lectures(added, updated, deleted)
                    except Exception as gcal_err:
                        import logging
                        logging.getLogger(__name__).error(f"Google Calendar sync failed: {str(gcal_err)}")
        except Exception as e:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.completed_at = datetime.utcnow()
                job.message = f"Error: {str(e)}"
                db.commit()

                # Send Slack notification to Status Channel
                slack_service.send_job_status(
                    title="❌ Sync Job Failed",
                    status="Failed",
                    message=f"Job ID: {job_id}\nError: {str(e)}"
                )
        finally:
            db.close()


    def get_job_status(self, db: Session, job_id: str):
        return db.query(Job).filter(Job.id == job_id).first()

    def get_jobs(self, db: Session, skip: int = 0, limit: int = 100):
        total = db.query(Job).count()
        items = db.query(Job).order_by(Job.completed_at.desc().nullslast()).offset(skip).limit(limit).all()
        return items, total

job_service = JobService()
