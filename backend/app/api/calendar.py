from fastapi import APIRouter, Request, HTTPException
from app.services.google_calendar import google_calendar_service
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/calendar", tags=["Calendar"])

class EventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime

@router.get("/auth")
async def google_auth():
    """구글 로그인 URL 반환"""
    auth_url = google_calendar_service.get_auth_url()
    return {"auth_url": auth_url}

@router.get("/callback")
async def google_callback(code: str):
    """구글 인증 콜백 처리"""
    try:
        google_calendar_service.fetch_token(code)
        return {"message": "Google Calendar connected successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-event")
async def create_event(event: EventCreate):
    """일정 생성 엔드포인트"""
    try:
        link = google_calendar_service.create_event(
            event.summary,
            event.description,
            event.start_time,
            event.end_time
        )
        if link:
            return {"status": "success", "event_link": link}
        else:
            raise HTTPException(status_code=500, detail="Failed to create event")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
