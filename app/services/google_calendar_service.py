import os.path
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import config

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        self.calendar_id = config.GOOGLE_CALENDAR_ID
        self.credentials_file = config.GOOGLE_SERVICE_ACCOUNT_FILE
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.service = None
        
        if self.calendar_id and self.credentials_file and os.path.exists(self.credentials_file):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_file, scopes=self.scopes)
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info("Google Calendar service initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Google Calendar service: {e}")
        else:
            if not self.calendar_id:
                logger.warning("GOOGLE_CALENDAR_ID not set. Google Calendar integration disabled.")
            if not self.credentials_file:
                logger.warning("GOOGLE_SERVICE_ACCOUNT_FILE not set. Google Calendar integration disabled.")
            elif not os.path.exists(self.credentials_file):
                logger.warning(f"Google credentials file not found at {self.credentials_file}. Integration disabled.")

    def _generate_event_id(self, lecture_dict: dict):
        """
        Generates a deterministic Google Calendar event ID based on date and time.
        Characters allowed: 0-9 and a-v (base32hex).
        """
        date_str = lecture_dict.get('date', '').replace('-', '') # YYYYMMDD
        time_str = lecture_dict.get('start_time', '').replace(':', '') # HHMM
        # Prefix with 'pk' to make it descriptive and ensure it starts with a letter if needed
        return f"pk{date_str}{time_str}00"

    def _prepare_event_body(self, lecture_dict: dict, event_id: str):
        """
        Prepares the event body for Google Calendar API.
        """
        date = lecture_dict.get('date')
        start_time = f"{date}T{lecture_dict.get('start_time')}:00"
        end_time = f"{date}T{lecture_dict.get('end_time', lecture_dict.get('start_time'))}:00"
        
        summary = lecture_dict.get('subject') or lecture_dict.get('summary')
        location = lecture_dict.get('room', '')
        
        description_parts = [
            f"Summary: {lecture_dict.get('summary')}",
            f"Teacher: {lecture_dict.get('teacher', 'N/A')}"
        ]
        if lecture_dict.get('type'):
            description_parts.append(f"Type: {lecture_dict.get('type')}")
        
        description = "\n".join(description_parts)

        return {
            'id': event_id,
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Warsaw',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Warsaw',
            }
        }

    def batch_sync_lectures(self, added: list, updated: list, deleted: list):
        """
        Synchronizes all changes in batches for better performance.
        First retrieves existing events to decide whether to insert or update.
        """
        if not self.service:
            return

        all_lectures = added + updated + deleted
        if not all_lectures:
            return

        # 1. First, check which events already exist in Google Calendar
        # We'll use a batch request to GET all relevant IDs
        existing_event_ids = set()
        id_to_lecture = {self._generate_event_id(l): l for l in all_lectures}
        event_ids_to_check = list(id_to_lecture.keys())

        logger.info(f"Checking existence of {len(event_ids_to_check)} events in Google Calendar...")

        # Batch GET requests
        batch_size = 50
        for i in range(0, len(event_ids_to_check), batch_size):
            chunk_ids = event_ids_to_check[i:i + batch_size]
            batch = self.service.new_batch_http_request()
            
            def get_callback(request_id, response, exception):
                if not exception:
                    existing_event_ids.add(response.get('id'))
                elif hasattr(exception, 'resp') and exception.resp.status != 404:
                    logger.error(f"Error checking event existence: {exception}")

            for eid in chunk_ids:
                batch.add(self.service.events().get(calendarId=self.calendar_id, eventId=eid), callback=get_callback)
            
            try:
                batch.execute()
            except Exception as e:
                logger.error(f"Error executing batch GET: {e}")

        logger.info(f"Found {len(existing_event_ids)} existing events in Google Calendar.")
        
        # 2. Build the final set of operations based on what actually exists
        final_ops = []
        
        # Deletions: only delete if it exists
        to_delete_count = 0
        for l in deleted:
            event_id = self._generate_event_id(l)
            if event_id in existing_event_ids:
                final_ops.append(self.service.events().delete(calendarId=self.calendar_id, eventId=event_id))
                to_delete_count += 1

        # Additions and Updates: route to insert or update based on existence
        to_insert_count = 0
        to_update_count = 0
        for l in (added + updated):
            event_id = self._generate_event_id(l)
            body = self._prepare_event_body(l, event_id)
            
            if event_id in existing_event_ids:
                final_ops.append(self.service.events().update(calendarId=self.calendar_id, eventId=event_id, body=body))
                to_update_count += 1
            else:
                final_ops.append(self.service.events().insert(calendarId=self.calendar_id, body=body))
                to_insert_count += 1

        if not final_ops:
            logger.info("No Google Calendar operations needed after verification.")
            return

        logger.info(f"Executing Google Calendar Batch: {to_delete_count} deletes, {to_insert_count} inserts, {to_update_count} updates.")

        # 3. Execute the final operations
        for i in range(0, len(final_ops), batch_size):
            chunk = final_ops[i:i + batch_size]
            batch = self.service.new_batch_http_request()
            
            def sync_callback(request_id, response, exception):
                if exception:
                    if hasattr(exception, 'resp') and exception.resp.status in [404, 409]:
                        return
                    logger.error(f"Batch operation error: {exception}")

            for op in chunk:
                batch.add(op, callback=sync_callback)
            
            try:
                batch.execute()
                logger.info(f"Successfully processed batch chunk of {len(chunk)} operations.")
            except Exception as e:
                logger.error(f"Error executing final Google Calendar batch: {e}")

    def upsert_event(self, lecture_dict: dict):
        """
        Creates or updates a calendar event for a lecture using a deterministic ID.
        """
        if not self.service:
            return

        pk_event_id = self._generate_event_id(lecture_dict)
        event_body = self._prepare_event_body(lecture_dict, pk_event_id)

        try:
            # Check if event already exists by ID
            try:
                self.service.events().get(calendarId=self.calendar_id, eventId=pk_event_id).execute()
                # If no error, it exists -> Update
                updated_event = self.service.events().update(
                    calendarId=self.calendar_id, 
                    eventId=pk_event_id, 
                    body=event_body
                ).execute()
                logger.info(f"Updated Google Calendar event (ID: {pk_event_id}): {event_body['summary']}")
                return updated_event
            except HttpError as e:
                if e.resp.status == 404:
                    # Not found -> Insert
                    new_event = self.service.events().insert(
                        calendarId=self.calendar_id, 
                        body=event_body
                    ).execute()
                    logger.info(f"Created Google Calendar event (ID: {pk_event_id}): {event_body['summary']}")
                    return new_event
                else:
                    raise e
        except HttpError as error:
            logger.error(f"An error occurred with Google Calendar API: {error}")
            return None

    def delete_event(self, lecture_dict: dict):
        """
        Deletes a calendar event using its deterministic ID.
        """
        if not self.service:
            return

        pk_event_id = self._generate_event_id(lecture_dict)
        try:
            self.service.events().delete(
                calendarId=self.calendar_id, 
                eventId=pk_event_id
            ).execute()
            logger.info(f"Deleted Google Calendar event (ID: {pk_event_id})")
        except HttpError as error:
            if error.resp.status == 404:
                logger.debug(f"Event {pk_event_id} already deleted or not found.")
            else:
                logger.error(f"Error deleting Google Calendar event {pk_event_id}: {error}")

google_calendar_service = GoogleCalendarService()
