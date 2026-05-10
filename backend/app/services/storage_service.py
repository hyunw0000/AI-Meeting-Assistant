import os
import json

DATA_DIR = "data"
MEETINGS_FILE = os.path.join(DATA_DIR, "meetings.json")

os.makedirs(DATA_DIR, exist_ok=True)

def load_meetings():
    if not os.path.exists(MEETINGS_FILE):
        return []

    if os.path.getsize(MEETINGS_FILE) == 0:
        return []

    with open(MEETINGS_FILE, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []

def save_meeting(meeting):
    meetings = load_meetings()
    meetings.append(meeting)

    with open(MEETINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(meetings, file, ensure_ascii=False, indent=2)

    return meeting

def get_meetings_by_date(date):
    meetings = load_meetings()
    return [
        meeting for meeting in meetings
        if meeting.get("meeting_date") == date
    ]

def get_calendar_events():
    meetings = load_meetings()
    events = []

    for meeting in meetings:
        meeting_result = meeting.get("meeting_result", {})
        tasks = meeting_result.get("tasks", [])

        for task in tasks:
            events.append({
                "title": task.get("content"),
                "date": task.get("due_date"),
                "assignee": task.get("assignee"),
                "meeting_id": meeting.get("id")
            })

    return events