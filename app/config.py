import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")

    PK_SHEET_REGEX = os.getenv("PK_SHEET_REGEX")
    PK_SCHEDULE_URL = os.getenv("PK_SCHEDULE_URL")

    SYNC_SCHEDULE = os.getenv("SYNC_SCHEDULE")
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
    SLACK_CHANNEL_JOB_STATUS = os.getenv("SLACK_CHANNEL_JOB_STATUS")
    SLACK_MENTIONS = os.getenv("SLACK_MENTIONS")
    GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    LECTURE_SHORTCUTS = {   
        # lectures
        "ZTBD": "Zaawansowane Technologie Baz Danych",
        "OE": "Obliczenia Ewolucyjne",
        "ZTP": "Zaawansowane Technologie Programowania",
        "TUM": "Technologie Uczenia Maszynowego",

        # teachers
        "WK": "Wojciech Książek",
        "DK": "Dominik Kulis",
        "HO": "Hubert Orlicki",
        "AP/SzSzom": "Anna Plichta / Szymon Szomiński"
    }

config = Config()

