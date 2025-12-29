import logging
import httpx
import pandas as pd
import io
import re
import asyncio
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from app.config import config
from app.models.jobs import Job
from app.models.lectures import Lecture
from app.services.ai_service import ai_service
from app.database import SessionLocal
from urllib.parse import urljoin
from datetime import datetime


logger = logging.getLogger(__name__)


async def _get_sheet_link(client: httpx.AsyncClient) -> str:
    """
    Scrapes the PK schedule page to find the link to the sheet.
    """
    logger.info(f"Scraping PK schedule page: {config.PK_SCHEDULE_URL}")
    response = await client.get(config.PK_SCHEDULE_URL)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    page_title = soup.title.string if soup.title else "No Title"
    logger.info(f"Successfully scraped page. Title: {page_title}")

    sheet_link = None
    for a in soup.find_all('a', href=True):
        if config.PK_SHEET_REGEX in a['href'].upper():
            sheet_link = a['href']
            break
    
    if sheet_link:
        if not sheet_link.startswith('http'):
            sheet_link = urljoin(config.PK_SCHEDULE_URL, sheet_link)
        logger.info(f"Found sheet link: {sheet_link}")
        return sheet_link
    
    logger.warning(f"Could not find a link containing regex: {config.PK_SHEET_REGEX}")
    raise Exception("Sheet link not found.")

def _is_link_changed(db: Session, job_id: str, sheet_link: str) -> bool:
    """
    Checks if the sheet link has changed since the last successful sync.
    """
    last_successful_job = db.query(Job).filter(
        Job.status == "completed",
        Job.id != job_id
    ).order_by(Job.completed_at.desc()).first()
    
    if last_successful_job and last_successful_job.sheet_url == sheet_link:
        logger.info("Sheet link has not changed since the last successful sync.")
        return False
    
    logger.info("Sheet link has changed or this is the first successful sync.")
    return True

async def _download_sheet(client: httpx.AsyncClient, sheet_url: str) -> bytes:
    """
    Downloads the sheet file content as bytes.
    """
    logger.info(f"Downloading sheet from: {sheet_url}")
    response = await client.get(sheet_url)
    response.raise_for_status()
    return response.content

def _retrieve_schedule_from_sheet(df: pd.DataFrame):
    """
    Ekstrahuje plan zajęć dla grupy DS1.
    Układ: Q (16) = Data, R (17) = Start, S (18) = Koniec, T (19) = DS1
    """
    # Indeksy kolumn (liczone od 0)
    COL_DATE = 16  # Q
    COL_START = 17 # R
    COL_END = 18   # S
    COL_DS1 = 19   # T
    
    # 1. Naprawa scalonych komórek dla Daty i obu kolumn Czasu
    # Używamy .iloc, aby uniknąć KeyError (odwołujemy się do pozycji)
    df.iloc[:, COL_DATE] = df.iloc[:, COL_DATE].ffill()
    df.iloc[:, COL_START] = df.iloc[:, COL_START].ffill()
    df.iloc[:, COL_END] = df.iloc[:, COL_END].ffill()

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    future_events = []

    for i in range(len(df)):
        # Pobieramy treść zajęć dla DS1
        cell_content = str(df.iat[i, COL_DS1]).strip()
        
        # Filtrujemy puste komórki i nagłówki
        if not cell_content or cell_content.lower() in ["nan", "ds1", "przedmiot"]:
            continue
            
        clean_text = re.sub(r'\s+', ' ', cell_content).strip()
        
        # Jeśli po wyczyszczeniu komórka jest pusta (były same spacje), pomijamy
        if not clean_text:
            continue

        raw_date_val = df.iat[i, COL_DATE]
        
        time_cell = str(df.iat[i, COL_START]).strip()
        
        start_t = 'nan'
        end_t = 'nan'
        
        if time_cell != 'nan':
            try:
                parts = [t.strip() for t in time_cell.split('-')]
                if len(parts) >= 2:
                    # Normalize to HH:MM
                    def normalize_time(t):
                        t = t.strip()
                        if ':' in t:
                            h, m = t.split(':')
                            return f"{int(h):02d}:{int(m):02d}"
                        return t
                    
                    start_t = normalize_time(parts[0])
                    end_t = normalize_time(parts[1])
            except Exception as te:
                logger.warning(f"Error parsing time cell '{time_cell}': {str(te)}")

        try:
            # 2. Parsowanie DATY
            if isinstance(raw_date_val, str):
                # Obsługa formatów typu "sobota 10/4/25" -> bierzemy tylko 10/4/25
                date_part = raw_date_val.split()[-1]
                event_date = datetime.strptime(date_part, '%d/%m/%y')
            elif isinstance(raw_date_val, datetime):
                event_date = raw_date_val
            else:
                continue

            # 3. FILTROWANIE: tylko od dzisiaj wzwyż
            if event_date < today:
                continue

            event = {
                "date": event_date.strftime('%Y-%m-%d'),
                "start_time": start_t,
                "end_time": end_t,
                "summary": clean_text
            }
            
            future_events.append(event)
    
        except Exception as e:
            # Logujemy błąd dla konkretnego wiersza, ale idziemy dalej
            continue

    return future_events

async def _sync_lectures_to_db(db: Session, job_id: str, schedule: list, sheet_url: str = None):
    """
    Synchronizes extracted schedule events with the database.
    Handles Added, Updated, and Deleted (Cancelled) cases.
    """
    if not schedule:
        logger.info("Sync completed: No events found in sheet.")
        return {"message": "No events found.", "added": [], "updated": [], "deleted": [], "sheet_url": sheet_url}

    # 1. Get existing lectures for the dates in the schedule to compare
    schedule_dates = list(set(event['date'] for event in schedule))
    existing_lectures = db.query(Lecture).filter(Lecture.date.in_(schedule_dates)).all()
    
    # Create a lookup map: (date, start, end) -> Lecture
    lookup = { (l.date, l.start_time, l.end_time): l for l in existing_lectures }
    
    added_lectures = []
    updated_lectures = []
    deleted_lectures = []
    
    seen_keys = set()
    to_enrich = [] # List for AI: {"id": lecture_id, "raw_text": summary}
    sync_id_map = {} # Track items for enrichment enrichment
    
    # Second pass: Process events from the sheet
    for event in schedule:
        key = (event['date'], event['start_time'], event['end_time'])
        seen_keys.add(key)
        existing_lecture = lookup.get(key)
        
        if existing_lecture:
            is_changed = existing_lecture.summary != event['summary']
            was_cancelled = existing_lecture.is_cancelled == 1
            
            if is_changed or was_cancelled:
                # Update details
                existing_lecture.summary = event['summary']
                existing_lecture.is_cancelled = 0 # Ensure it's active
                existing_lecture.last_sync_id = job_id
                
                # Reset AI fields for re-enrichment
                existing_lecture.subject = None
                existing_lecture.type = None
                existing_lecture.teacher = None
                existing_lecture.room = None
                
                updated_lectures.append(existing_lecture)
                sync_id_map[id(existing_lecture)] = existing_lecture
                to_enrich.append({"id": id(existing_lecture), "raw_text": event['summary']})
            else:
                # No change, just update sync ID
                existing_lecture.last_sync_id = job_id
        else:
            # New event
            new_lecture = Lecture(
                date=event['date'],
                start_time=event['start_time'],
                end_time=event['end_time'],
                summary=event['summary'],
                last_sync_id=job_id,
                is_cancelled=0
            )
            db.add(new_lecture)
            added_lectures.append(new_lecture)
            sync_id_map[id(new_lecture)] = new_lecture
            to_enrich.append({"id": id(new_lecture), "raw_text": event['summary']})

    # Third pass: Handle deletions
    # Any lecture in DB for these dates that wasn't in the sheet should be marked cancelled
    for l in existing_lectures:
        key = (l.date, l.start_time, l.end_time)
        if key not in seen_keys and l.is_cancelled == 0:
            l.is_cancelled = 1
            l.last_sync_id = job_id
            deleted_lectures.append(l)

    db.flush()
    
    # 2. AI Enrichment Step
    if to_enrich:
        enriched_results = await ai_service.enrich_lectures(to_enrich)
        for res in enriched_results:
            ext_id = res.get("id")
            lecture_obj = sync_id_map.get(ext_id)
            if lecture_obj:
                lecture_obj.subject = res.get("subject")
                lecture_obj.type = res.get("type")
                lecture_obj.teacher = res.get("teacher")
                lecture_obj.room = res.get("room")
                
    db.commit()
    
    summary_msg = f"Sync processed. Added: {len(added_lectures)}, Updated: {len(updated_lectures)}, Deleted: {len(deleted_lectures)}."
    logger.info(summary_msg)
    
    # Helper to convert models to dicts for notification (avoids session issues)
    def to_dict(l):
        return {
            "date": l.date,
            "start_time": l.start_time,
            "end_time": l.end_time,
            "subject": l.subject,
            "summary": l.summary,
            "room": l.room,
            "teacher": l.teacher,
            "type": l.type,
            "is_cancelled": l.is_cancelled
        }

    return {
        "message": summary_msg,
        "added": [to_dict(l) for l in added_lectures],
        "updated": [to_dict(l) for l in updated_lectures],
        "deleted": [to_dict(l) for l in deleted_lectures],
        "sheet_url": sheet_url
    }

async def run_sync_job(job_id: str):
    """
    PK schedule synchronization job.
    """
    logger.info(f"Starting PK Schedule Sync Job for job_id: {job_id}...")
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        db = SessionLocal()
        try:
            # 1. Scrape PK page and retrieve sheet link
            sheet_link = await _get_sheet_link(client)
            
            # Update current job with the found link immediately
            current_job = db.query(Job).filter(Job.id == job_id).first()
            if current_job:
                current_job.sheet_url = sheet_link
                db.commit()

            # 2. Validation: check if link has changed
            if not _is_link_changed(db, job_id, sheet_link):
                return {"message": "Sync completed: Sheet link has not changed.", "changed_lectures": [], "sheet_url": sheet_link}

            # 3. Load sheet in memory
            sheet_content = await _download_sheet(client, sheet_link)
            
            # Load into pandas
            # xlrd for .xls, openpyxl for .xlsx
            df = pd.read_excel(io.BytesIO(sheet_content), header=None)
            
            logger.info(f"Successfully loaded sheet into memory. Shape: {df.shape}")
            
            schedule = _retrieve_schedule_from_sheet(df)
            logger.info(f"Extracted {len(schedule)} future events from sheet.")

            return await _sync_lectures_to_db(db, job_id, schedule, sheet_url=sheet_link)

        except Exception as e:
            logger.error(f"Error during sync job: {str(e)}")
            raise e
        finally:
            db.close()

