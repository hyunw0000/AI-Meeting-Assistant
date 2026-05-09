import re


def generate_meeting_result(transcript):
    tasks = extract_tasks(transcript)

    return {
        "title": "회의록",
        "summary": generate_summary(transcript),
        "decisions": generate_decisions(transcript),
        "tasks": tasks
    }


def generate_summary(transcript):
    if not transcript:
        return "음성 인식 결과가 없습니다."

    if len(transcript) > 120:
        return transcript[:120] + "..."

    return transcript


def generate_decisions(transcript):
    if not transcript:
        return []

    return [
        "회의 내용을 바탕으로 후속 작업을 정리했습니다."
    ]


def extract_tasks(transcript):
    tasks = []

    if not transcript:
        return tasks

    # YYYY-MM-DD 형식 날짜 추출
    date_patterns = re.findall(r"\d{4}-\d{2}-\d{2}", transcript)

    for date in date_patterns:
        tasks.append({
            "content": "회의에서 언급된 일정",
            "assignee": "미정",
            "due_date": date
        })

    return tasks