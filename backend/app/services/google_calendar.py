import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarService:
    def __init__(self):
        self.creds = None
        # The file token.json stores the user's access and refresh tokens.
        # It is created automatically when the authorization flow completes for the first time.
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    def get_auth_url(self):
        """인증 URL 생성"""
        flow = InstalledAppFlow.from_client_config(
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
        auth_url, _ = flow.authorization_url(prompt="consent")
        return auth_url

    def fetch_token(self, code):
        """인증 코드로 토큰 획득"""
        flow = InstalledAppFlow.from_client_config(
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
        flow.fetch_token(code=code)
        self.creds = flow.credentials
        
        # 토큰 저장 (실제 서비스에서는 DB나 안전한 저장소 사용 권장)
        with open("token.json", "w") as token:
            token.write(self.creds.to_json())
        
        return self.creds

    def create_event(self, summary, description, start_time, end_time):
        """구글 캘린더에 일정 생성"""
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                raise Exception("Google Calendar 인증이 필요합니다.")

        try:
            service = build("calendar", "v3", credentials=self.creds)

            event = {
                "summary": summary,
                "description": description,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "Asia/Seoul",
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "Asia/Seoul",
                },
            }

            event = service.events().insert(calendarId="primary", body=event).execute()
            return event.get("htmlLink")

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

google_calendar_service = GoogleCalendarService()
