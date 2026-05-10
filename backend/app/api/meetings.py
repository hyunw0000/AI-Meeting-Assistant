from fastapi import APIRouter, UploadFile, File, Form, Query
import os
import shutil
from datetime import datetime

from app.services.stt_service import speech_to_text
from app.services.meeting_service import generate_meeting_result
from app.services.storage_service import (
    save_meeting,
    get_meetings_by_date,
    get_calendar_events
)

router = APIRouter(prefix="/meetings", tags=["Meetings"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/audio")
async def upload_audio(
    file: UploadFile = File(...),
    source: str = Form("upload"),
    meeting_date: str = Form(None)
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if meeting_date is None:
        meeting_date = datetime.now().strftime("%Y-%m-%d")

    stt_result = speech_to_text(file_path)
    meeting_result = generate_meeting_result(stt_result)

    meeting = {
        "id": timestamp,
        "source": source,
        "original_filename": file.filename,
        "saved_filename": saved_filename,
        "file_path": file_path,
        "meeting_date": meeting_date,
        "transcript": stt_result,
        "meeting_result": meeting_result,
        "created_at": datetime.now().isoformat()
    }

    save_meeting(meeting)

    return {
        "message": "audio saved and analyzed",
        "meeting": meeting
    }


@router.get("/date")
def get_meetings_by_meeting_date(date: str = Query(...)):
    meetings = get_meetings_by_date(date)

    return {
        "date": date,
        "count": len(meetings),
        "meetings": meetings
    }


@router.get("/calendar/events")
def get_events():
    events = get_calendar_events()

    return {
        "count": len(events),
        "events": events
    }