from sqlalchemy import Column, String, DateTime
from app.database import Base
import uuid
from datetime import datetime

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    message = Column(String, nullable=True)
    sheet_url = Column(String, nullable=True)
    triggered_by = Column(String, default="system")

