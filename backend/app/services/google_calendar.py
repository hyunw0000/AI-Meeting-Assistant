import os.path
import requests as req
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

class GoogleCalendarService:
    def __init__(self):
        self.creds = None
        if os.path.exists("token.json"):
            try:
                self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            except Exception as e:
                print(f"기존 token.json 로드 실패: {e}")
                self.creds = None

    def get_user_info(self):
        """인증된 사용자의 정보를 가져옵니다."""
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    with open("token.json", "w") as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                    print(f"토큰 갱신 실패: {e}")
                    return None
            else:
                return None
        
        try:
            service = build("oauth2", "v2", credentials=self.creds)
            user_info = service.userinfo().get().execute()
            return {
                "name": user_info.get("name"),
                "email": user_info.get("email"),
                "picture": user_info.get("picture")
            }
        except Exception as e:
            print(f"사용자 정보 획득 실패 (상세): {e}")
            return None

    def get_auth_url(self):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        auth_url, state = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true"
        )
        
        with open("verifier.txt", "w") as f:
            f.write(flow.code_verifier)
            
        return auth_url

    def fetch_token(self, code):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        if os.path.exists("verifier.txt"):
            with open("verifier.txt", "r") as f:
                flow.code_verifier = f.read()
        
        # OAuth2Token 반환값을 Credentials 객체로 변환
        token_info = flow.fetch_token(code=code)
        self.creds = Credentials(
            token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES
        )
        
        with open("token.json", "w") as token:
            token.write(self.creds.to_json())
            
        return self.creds

    def get_events(self):
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    return None
            else:
                return None
        try:
            service = build("calendar", "v3", credentials=self.creds)
            # 오늘부터 향후 30일간의 일정 조회
            now = datetime.utcnow().isoformat() + "Z"
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=50,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            return events_result.get("items", [])
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

#구글 캘린더 이벤트 생성 신규 추가 
    def create_event(self, summary, description, start_time, end_time):
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    return None
            else:
                return None
        try:
            service = build("calendar", "v3", credentials=self.creds)
            event = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Seoul"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Seoul"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 1440},
                        {"method": "popup", "minutes": 30},
                    ]
                }
            }
            result = service.events().insert(calendarId="primary", body=event).execute()
            return result.get("htmlLink")
        except HttpError as e:
            print(f"캘린더 이벤트 생성 실패: {e}")
            return None

google_calendar_service = GoogleCalendarService()
