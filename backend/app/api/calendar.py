from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from app.services.google_calendar import google_calendar_service
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
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

@router.get("/status")
async def auth_status():
    is_logged_in = os.path.exists("token.json")
    return {"is_logged_in": is_logged_in}

@router.get("/callback")
async def google_callback(code: str):
    try:
        google_calendar_service.fetch_token(code)
        return RedirectResponse(url="http://101.79.22.220?login=success")  # ✅ 리다이렉트
    except Exception as e:
        return RedirectResponse(url="http://101.79.22.220?login=error")

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