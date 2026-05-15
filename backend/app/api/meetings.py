from fastapi import APIRouter, UploadFile, File, Form, Query, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import shutil
from datetime import datetime, timedelta #timedelta 추가

from app.core.database import get_db
from app.models.meeting import Meeting
from app.services.stt_service import speech_to_text
from app.services.meeting_service import generate_meeting_result
from app.services.google_calendar import google_calendar_service

router = APIRouter(prefix="/meetings", tags=["Meetings"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/audio")
async def upload_audio(
    file: UploadFile = File(...),
    source: str = Form("upload"),
    meeting_date: str = Form(None),
    title: str = Form(None),
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
    meeting_result = generate_meeting_result(stt_result, meeting_date)

    db_meeting = Meeting(
        title=title if title else meeting_result.get("title", "회의록"),
        date=datetime.strptime(meeting_date, "%Y-%m-%d"),
        summary=meeting_result.get("summary", ""),
        action_items=[],
        transcript=stt_result,
        file_url=file_path,
    )
    
    # 구글 캘린더 자동 등록
    tasks = meeting_result.get("tasks", [])
    for task in tasks:
        due_date = task.get("due_date")
        if due_date:
            try:
                start_time = datetime.strptime(due_date, "%Y-%m-%d")
                end_time = start_time + timedelta(hours=1)
                description = f"담당자: {task.get('assignee', '미정')}"
                google_calendar_service.create_event(
                    summary=task.get("content", "할 일"),
                    description=description,
                    start_time=start_time,
                    end_time=end_time
                )
            except Exception as e:
                print(f"구글 캘린더 등록 실패: {e}")

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
                "memo": meeting.memo,
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
        # 1. 회의 자체를 캘린더에 표시
        events.append({
            "id": meeting.id,
            "title": meeting.title,
            "date": meeting.date.strftime("%Y-%m-%d"),
            "type": "meeting",
            "meeting_id": meeting.id,
        })

        # 2. 회의에서 나온 할 일도 due_date가 있으면 캘린더에 표시
        tasks = meeting.action_items or []

        for task in tasks:
            due_date = task.get("due_date")

            if due_date:
                events.append({
                    "id": f"{meeting.id}_{due_date}_{task.get('content')}",
                    "title": task.get("content"),
                    "date": due_date,
                    "assignee": task.get("assignee"),
                    "type": "task",
                    "meeting_id": meeting.id,
                })

    return {
        "count": len(events),
        "events": events,
    }

@router.delete("/{meeting_id}")
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

    if meeting is None:
        raise HTTPException(status_code=404, detail="회의를 찾을 수 없습니다")
    
    db.delete(meeting)
    db.commit()

    return {
        "success": True,
        "message": "회의가 삭제되었습니다.",
        "deleted_id": meeting_id,
    }

class MemoUpdateRequest(BaseModel):
    memo: Optional[str] = ""

@router.patch("/{meeting_id}/memo")
def update_meeting_memo(
    meeting_id: int,
    request: MemoUpdateRequest,
    db: Session = Depends(get_db),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

    if meeting is None:
        return {
            "success": False,
            "message": "회의를 찾을 수 없습니다.",
        }

    meeting.memo = request.memo
    db.commit()
    db.refresh(meeting)

    return {
        "success": True,
        "meeting_id": meeting.id,
        "memo": meeting.memo,
    }
