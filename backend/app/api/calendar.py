from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from app.services.google_calendar import google_calendar_service
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.core.config import settings
import os

router = APIRouter(prefix="/calendar", tags=["Calendar"])

class EventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime

@router.get("/auth")
async def google_auth():
    auth_url = google_calendar_service.get_auth_url()
    return {"auth_url": auth_url}

@router.get("/events")
async def get_events():
    try:
        events = google_calendar_service.get_events()
        if events is None:
            raise HTTPException(status_code=401, detail="인증이 필요합니다.")
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def auth_status():
    is_token_exists = os.path.exists("token.json")
    user_info = None
    
    if is_token_exists:
        user_info = google_calendar_service.get_user_info()
    
    # 사용자 정보를 못 가져와도 토큰이 있으면 일단 로그인 된 것으로 간주
    return {
        "is_logged_in": is_token_exists,
        "user": user_info or {
            "name": "사용자",
            "email": "정보를 불러올 수 없음",
            "picture": None
        }
    }

@router.get("/callback")
async def google_callback(code: str):
    try:
        creds = google_calendar_service.fetch_token(code)
        print(f"DEBUG: 콜백에서 받은 creds 확인: {creds}")
        if not creds:
            raise Exception("토큰 획득 실패")
        # 로컬 테스트 시 localhost:5173으로, 서버 배포 시 해당 IP로 이동
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?login=success")
    except Exception as e:
        print(f"로그인 콜백 에러: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?login=error")

@router.post("/create-event")
async def create_event(event: EventCreate):
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
