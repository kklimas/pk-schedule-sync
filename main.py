from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.api.routers import jobs, lectures
from app.database import engine, Base
from app.scheduler import start_scheduler, stop_scheduler
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import time

# Ensure the system timezone (set in Dockerfile) is applied to the Python process
if os.name != 'nt':  # tzset is not available on Windows
    time.tzset()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(process)d] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %z",
)

api_prefix = '/api/v1'

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PK Schedule Sync API")

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()

# Mount the 'ui' directory for static files
ui_path = os.path.join(os.path.dirname(__file__), "ui")
app.mount("/static", StaticFiles(directory=ui_path), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(ui_path, "index.html"))

# Also serve style.css and app.js from the root for simplicity in index.html
@app.get("/style.css")
async def read_css():
    return FileResponse(os.path.join(ui_path, "style.css"))

@app.get("/app.js")
async def read_js():
    return FileResponse(os.path.join(ui_path, "app.js"))

app.include_router(jobs.router, prefix=f'{api_prefix}/jobs', tags=["jobs"])
app.include_router(lectures.router, prefix=f'{api_prefix}/lectures', tags=["lectures"])
