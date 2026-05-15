from datetime import datetime, timedelta
import json
import re
import requests

# 1. URL - /api/generate → /generate
OLLAMA_URL = "http://10.0.30.6:8001/generate"
#MODEL_NAME = "qwen2.5:7b"


def generate_meeting_result(transcript, meeting_date=None):
    if not transcript:
        return fallback_result("")

    base_date = (
        datetime.strptime(meeting_date, "%Y-%m-%d").date()
        if meeting_date
        else datetime.now().date()
    )

    prompt = f"""
너는 회의록 작성 AI야.
아래 회의 텍스트를 분석해서 반드시 JSON만 반환해.

반환 형식:
{{
  "title": "회의 제목",
  "summary": "회의 요약",
  "decisions": ["결정사항1", "결정사항2"],
  "tasks": [
    {{
      "content": "할 일",
      "assignee": "담당자 또는 미정",
      "due_text": "원문에 나온 마감 표현",
      "due_date": null
    }}
  ]
}}

규칙:
- 설명 문장 없이 JSON만 반환해.
- summary는 회의 전체 내용을 2~4문장으로 요약해.
- 특정 할 일 하나만 요약하지 말고, 회의에서 논의된 전체 작업 흐름을 요약해.

- 회의 텍스트에서 담당자, 해야 할 일, 마감일이 언급된 항목은 모두 tasks에 넣어.
- 한 문장 안에 여러 개의 할 일이 있으면 각각 별도 task로 분리해.
- 단순 인사, 회의 시작 안내, 마무리 문장은 tasks에 넣지 마.

- content는 원문 문장 그대로 쓰지 말고, 핵심 할 일만 짧게 써.
- content에는 담당자 이름, 마감일 표현, “해주세요”, “하기로 했습니다”를 넣지 마.
- content는 회의 텍스트에서 실제로 언급된 할 일만 짧게 써.

- assignee에는 회의 텍스트에서 언급된 담당자 이름만 넣어. 텍스트에 없는 이름은 절대 쓰지 마.
- 담당자가 없으면 assignee는 "미정"으로 해.
- 회의 텍스트에 없는 할 일은 절대 만들어내지 마.
- 할 일이 없으면 tasks는 빈 배열 []로 반환해.

- due_text에는 원문에 나온 날짜 표현만 그대로 넣어.
- due_text 예시: "내일까지", "이번 주 금요일까지", "5월 20일까지", "다음 주 월요일까지", "오늘 안으로"
- due_date는 네가 계산하지 말고 null로 둬.

- 오늘 날짜 기준은 {base_date.isoformat()}야.

회의 텍스트:
{transcript}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "prompt": prompt,
                "max_tokens": 1000,   # 기본값 256이라 회의록엔 너무 짧음
                "temperature": 0.7,
            },
            timeout=300
        )

        result = response.json()
        content = result.get("response", "")

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
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    try:
        json_text = re.search(r"\{.*\}", content, re.DOTALL).group()
        return json.loads(json_text)
    except Exception:
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

    fixed_tasks = supplement_tasks_from_transcript(
        fixed_tasks,
        transcript,
        base_date
    )

    return fixed_tasks
