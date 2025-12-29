from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.job_service import job_service
from app.database import SessionLocal
from app.config import config
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def scheduled_sync_job():
    db = SessionLocal()
    try:
        # We call the service that manages job creation and execution
        await job_service.execute_sync(db, triggered_by="system")
        logger.info("Scheduled sync job finished successfully.")
    except Exception as e:
        logger.error(f"Error during scheduled sync job: {str(e)}")
    finally:
        db.close()

import os
import fcntl

# Keep handle global so it's not garbage collected (which would release the lock)
_lock_file_handle = None

def start_scheduler():
    """
    Initializes and starts the scheduler.
    Uses a file lock to ensure only one worker starts it in a multi-worker environment.
    """
    global _lock_file_handle
    if not scheduler.running:
        # Use a file lock to ensure only one process starts the scheduler
        lock_file = "/tmp/scheduler.lock"
        try:
            _lock_file_handle = open(lock_file, "w")
            fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            scheduler.add_job(
                scheduled_sync_job, 
                CronTrigger.from_crontab(config.SYNC_SCHEDULE),
                id="sync_job_scheduled",
                replace_existing=True,
                misfire_grace_time=3600,
                coalesce=True
            )
            scheduler.start()
            logger.info(f"APScheduler started: Sync job scheduled with: {config.SYNC_SCHEDULE}")
        except (IOError, BlockingIOError):
            # Another worker already has the lock, this is expected
            _lock_file_handle = None
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

def stop_scheduler():
    """
    Shuts down the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")
