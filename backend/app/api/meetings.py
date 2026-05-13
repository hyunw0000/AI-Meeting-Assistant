from fastapi import APIRouter, UploadFile, File, Form, Query, Depends
from sqlalchemy.orm import Session
import os
import shutil
from datetime import datetime

from app.core.database import get_db
from app.models.meeting import Meeting
from app.services.stt_service import speech_to_text
from app.services.meeting_service import generate_meeting_result

router = APIRouter(prefix="/meetings", tags=["Meetings"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/audio")
async def upload_audio(
    file: UploadFile = File(...),
    source: str = Form("upload"),
    meeting_date: str = Form(None),
    db: Session = Depends(get_db),
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

    db_meeting = Meeting(
        title=meeting_result.get("title", "회의록"),
        date=datetime.strptime(meeting_date, "%Y-%m-%d"),
        summary=meeting_result.get("summary", ""),
        action_items=meeting_result.get("tasks", []),
        transcript=stt_result,
        file_url=file_path,
    )

    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)

    return {
        "message": "audio saved and analyzed",
        "meeting": {
            "id": db_meeting.id,
            "source": source,
            "original_filename": file.filename,
            "saved_filename": saved_filename,
            "file_path": file_path,
            "meeting_date": meeting_date,
            "transcript": stt_result,
            "meeting_result": meeting_result,
            "created_at": db_meeting.created_at,
        },
    }


@router.get("/date")
def get_meetings_by_meeting_date(
    date: str = Query(...),
    db: Session = Depends(get_db),
):
    target_date = datetime.strptime(date, "%Y-%m-%d").date()

    meetings = db.query(Meeting).all()

    result = []
    for meeting in meetings:
        if meeting.date.date() == target_date:
            result.append({
                "id": meeting.id,
                "title": meeting.title,
                "meeting_date": meeting.date.strftime("%Y-%m-%d"),
                "summary": meeting.summary,
                "tasks": meeting.action_items,
                "transcript": meeting.transcript,
                "file_url": meeting.file_url,
                "created_at": meeting.created_at,
            })

    return {
        "date": date,
        "count": len(result),
        "meetings": result,
    }


@router.get("/calendar/events")
def get_events(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).all()
    events = []

    for meeting in meetings:
        tasks = meeting.action_items or []

        for task in tasks:
            due_date = task.get("due_date")

            if due_date:
                events.append({
                    "title": task.get("content"),
                    "date": due_date,
                    "assignee": task.get("assignee"),
                    "meeting_id": meeting.id,
                })

    return {
        "count": len(events),
        "events": events,
    }