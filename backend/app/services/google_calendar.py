import os.path
import requests as req
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarService:
    def __init__(self):
        self.creds = None
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    def get_auth_url(self):
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
        auth_url, _ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
        )
        return auth_url

    def fetch_token(self, code):
        token_response = req.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )
        token_data = token_response.json()
        self.creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        with open("token.json", "w") as token:
            token.write(self.creds.to_json())
        return self.creds

    def create_event(self, summary, description, start_time, end_time):
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
                "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Seoul"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Seoul"},
            }
            event = service.events().insert(calendarId="primary", body=event).execute()
            return event.get("htmlLink")
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

google_calendar_service = GoogleCalendarService()