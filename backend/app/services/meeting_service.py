from datetime import datetime, timedelta
import json
import re
import requests

import os
from dotenv import load_dotenv

load_dotenv()

# 환경변수에서 선택된 서버의 URL을 가져옴
server_mode = os.getenv("ACTIVE_OLLAMA_SERVER", "LOCAL")
OLLAMA_URL = os.getenv("TEAM_OLLAMA_URL") if server_mode == "TEAM" else os.getenv("LOCAL_OLLAMA_URL")
MODEL_NAME = "qwen2.5:7b"


def generate_meeting_result(transcript, meeting_date=None):
    if not transcript:
        return fallback_result("")

    base_date = (
        datetime.strptime(meeting_date, "%Y-%m-%d").date()
        if meeting_date
        else datetime.now().date()
    )

    prompt = f"""너는 회의록 작성 AI야. 아래 규칙을 엄격히 지켜서 반드시 JSON만 반환해.

[규칙]
- 반드시 중괄호{{ 로 시작해.
- JSON 외 다른 문장(서론, 설명) 절대 출력하지 마.
- summary 필드는 줄글로 풀어쓰지 말고, "라벨: 내용" 형식으로 한 줄에 하나씩 작성해.
- 회의 텍스트에 명시된 내용만 사용하고, 추측하지 마.
- 오늘 날짜 기준은 {base_date.isoformat()}.
- 나머지 JSON 구조는 아래 형식을 반드시 따라.

[JSON 형식]
{{
  "title": "회의 제목",
  "summary": "주제: ... \n참여자: ... \n안건: ... \n주요 논의: ... \n다음 회의: ...",
  "decisions": ["결정사항1", "결정사항2"],
  "tasks": [
    {{"content": "할 일", "assignee": "담당자", "due_text": "원문 날짜", "due_date": null}}
  ]
}}

[회의 텍스트 시작]
{transcript}
[회의 텍스트 끝]
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=600
        )

        result = response.json()
        content = result.get("response", "")

        print("=" * 50)
        print("DEBUG LLM 응답:", content[:2000])
        print("=" * 50)
        
        parsed_result = parse_llm_json(content, transcript)

        fixed_tasks = fix_due_dates(
            parsed_result.get("tasks", []),
            transcript,
            base_date
        )

        parsed_result["tasks"] = fixed_tasks

        return parsed_result

    except Exception as e:
        print("LLM 호출 실패:", e)
        return fallback_result(transcript)


def parse_llm_json(content, transcript):
    try:
        # JSON 문자열 내부의 줄바꿈 문자를 제거하여 파싱 에러 방지
        content = content.replace('\n', ' ')
        
        # JSON처럼 보이는 가장 긴 { ... } 블록 추출
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            return json.loads(json_str)
    except Exception as e:
        print("JSON 파싱 에러:", e)
        
    return fallback_result(transcript)


def fallback_result(transcript):
    return {
        "title": "회의록",
        "summary": transcript[:120] + "..." if len(transcript) > 120 else transcript,
        "decisions": [],
        "tasks": []
    }


def get_this_weekday(base_date, weekday):
    current_weekday = base_date.weekday()
    days = weekday - current_weekday
    return base_date + timedelta(days=days)


def get_next_week_weekday(base_date, weekday):
    current_weekday = base_date.weekday()
    days = 7 - current_weekday + weekday
    return base_date + timedelta(days=days)


def parse_due_date_from_text(text, base_date):
    if not text:
        return None

    compact = text.replace(" ", "")

    if "내일" in compact:
        return (base_date + timedelta(days=1)).isoformat()

    if "모레" in compact:
        return (base_date + timedelta(days=2)).isoformat()

    if "오늘" in compact or "오늘안" in compact:
        return base_date.isoformat()

    weekdays = {
        "월요일": 0,
        "화요일": 1,
        "수요일": 2,
        "목요일": 3,
        "금요일": 4,
        "토요일": 5,
        "일요일": 6,
    }

    for name, weekday in weekdays.items():
        if f"다음주{name}" in compact:
            return get_next_week_weekday(base_date, weekday).isoformat()

    for name, weekday in weekdays.items():
        if f"이번주{name}" in compact:
            return get_this_weekday(base_date, weekday).isoformat()

    for name, weekday in weekdays.items():
        if name in compact:
            return get_this_weekday(base_date, weekday).isoformat()

    match = re.search(r"(\d{1,2})월(\d{1,2})일", compact)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        return datetime(base_date.year, month, day).date().isoformat()

    return None


def extract_assignee_from_text(text):
    match = re.search(r"담당자는\s*([가-힣A-Za-z0-9]+)", text)
    if match:
        return match.group(1)

    match = re.search(r"([가-힣A-Za-z0-9]+)(?:가|이)\s*맡", text)
    if match:
        return match.group(1)

    match = re.search(r"([가-힣A-Za-z0-9]+)(?:가|이)\s*담당", text)
    if match:
        return match.group(1)

    return "미정"


def normalize_content(text):
    content = text.strip()
    content = re.sub(r"^화자\d+:\s*", "", content)
    content = re.sub(r"^(그리고|추가로|우선)\s*", "", content)
    return content.strip()


def is_task_like_sentence(text):
    task_keywords = [
        "완료", "구현", "진행", "수정", "테스트", "작성",
        "개선", "연동", "업로드", "저장", "디자인", "전달",
        "개발", "검토", "확인", "정리"
    ]

    ignore_keywords = [
        "회의 시작", "오늘 회의", "시작하겠습니다", "이상입니다",
        "마치겠습니다", "수고하셨습니다"
    ]

    if any(keyword in text for keyword in ignore_keywords):
        return False

    return any(keyword in text for keyword in task_keywords)


def is_similar_task_exists(tasks, chunk):
    compact_chunk = chunk.replace(" ", "")

    for task in tasks:
        content = task.get("content", "")
        compact_content = content.replace(" ", "")

        if not compact_content:
            continue

        if compact_content in compact_chunk:
            return True

        if compact_chunk in compact_content:
            return True

        if compact_chunk[:15] and compact_chunk[:15] in compact_content:
            return True

        if compact_content[:15] and compact_content[:15] in compact_chunk:
            return True

    return False


def supplement_tasks_from_transcript(tasks, transcript, base_date):
    result = tasks[:]
    chunks = re.split(r"[.\n]", transcript)

    for chunk in chunks:
        chunk = chunk.strip()

        if not chunk:
            continue

        due_date = parse_due_date_from_text(chunk, base_date)

        if due_date is None:
            continue

        if not is_task_like_sentence(chunk):
            continue

        if is_similar_task_exists(result, chunk):
            continue

        content = normalize_content(chunk)
        assignee = extract_assignee_from_text(chunk)

        result.append({
            "content": content,
            "assignee": assignee,
            "due_text": chunk,
            "due_date": due_date
        })

    return result


def fix_due_dates(tasks, transcript, base_date):
    fixed_tasks = []

    for task in tasks:
        due_text = task.get("due_text", "")
        content = task.get("content", "")

        parsed_date = parse_due_date_from_text(due_text, base_date)

        if parsed_date is None:
            parsed_date = parse_due_date_from_text(content, base_date)

        task["due_date"] = parsed_date

        if task.get("assignee") in [None, "", "미정"]:
            task["assignee"] = extract_assignee_from_text(due_text + " " + content)

        fixed_tasks.append(task)

    #fixed_tasks = supplement_tasks_from_transcript(
    #    fixed_tasks,
    #    transcript,
    #    base_date
    #)

    return fixed_tasks
