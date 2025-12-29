from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(String, index=True) # YYYY-MM-DD
    start_time = Column(String) # HH:MM
    end_time = Column(String)   # HH:MM
    summary = Column(String)
    subject = Column(String, nullable=True)
    type = Column(String, nullable=True)
    teacher = Column(String, nullable=True)
    room = Column(String, nullable=True)
    last_sync_id = Column(String, ForeignKey("jobs.id"), nullable=True) # Link to Job ID
    last_sync = relationship("Job")
    is_cancelled = Column(Integer, default=0) # 0 = false, 1 = true (using Integer for SQLite compatibility/simplicity)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
