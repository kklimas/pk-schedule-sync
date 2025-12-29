from sqlalchemy.orm import Session
from app.models.lectures import Lecture
from app.models.jobs import Job
from datetime import datetime

class LectureService:
    def get_lectures(self, db: Session, skip: int = 0, limit: int = 100):
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        query = db.query(Lecture).filter(
            Lecture.date >= today_str,
            Lecture.is_cancelled == 0
        )
        
        total = query.count()
        
        items = query.order_by(Lecture.date.asc(), Lecture.start_time.asc()) \
                     .offset(skip) \
                     .limit(limit) \
                     .all()
        
        return items, total

lecture_service = LectureService()
