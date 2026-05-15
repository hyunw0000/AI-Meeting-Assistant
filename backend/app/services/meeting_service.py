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
- summary는 다음 항목 순서대로 작성하고, 각 항목 사이에 \n을 넣어 줄바꿈해.
- 형식 (대괄호와 설명은 실제 내용으로 채워):
  [주제]: 회의 제목
  [참여자]: 참석자 이름들 쉼표로 나열
  [안건]: 안건들 쉼표로 나열
  [주요 논의]: 각 참석자별 담당 작업과 마감일
  [다음 회의]: 다음 회의 일정
- 추측이나 결론 만들기 금지. "목표로 합니다", "예정입니다" 같은 추측성 마무리 문장 금지.
- summary 끝에 원문에 없는 마무리 문장을 추가하지 마.
- 회의 텍스트에 명시된 내용만 사용해. 추측 금지.
- 회의 텍스트에 없는 항목은 아예 생략해.
- 대괄호와 한글 라벨은 그대로 유지하고, 콜론 뒤에 실제 내용을 채워.

- 회의 텍스트에서 담당자, 해야 할 일, 마감일이 언급된 항목은 모두 tasks에 넣어.
- 한 문장 안에 여러 개의 할 일이 있으면 각각 별도 task로 분리해.
- 단순 인사, 회의 시작 안내, 마무리 문장은 tasks에 넣지 마.

- content는 원문 문장 그대로 쓰지 말고, 핵심 할 일만 짧게 써.
- content에는 담당자 이름, 마감일 표현, “해주세요”, “하기로 했습니다”를 넣지 마.
- content는 회의 텍스트에서 실제로 언급된 할 일만 짧게 써.

- 회의 텍스트에 없는 내용은 절대 만들지 마.
- 텍스트가 짧거나 내용이 부족하면 summary에 "회의 내용이 충분하지 않습니다"라고 써.
- tasks와 decisions도 텍스트에 명시된 것만 넣어.

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
    # 마크다운 코드블록 제거
    content = re.sub(r"```json\s*", "", content)
    content = re.sub(r"```\s*", "", content)
    content = content.strip()

    # 1. 순수 JSON 파싱 시도
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 2. 앞에 자연어가 붙는 경우 - 모든 { 위치 찾아서 마지막부터 시도
    matches = list(re.finditer(r"\{", content))
    for m in matches:
        candidate = content[m.start():]
        depth = 0
        end = -1
        for i, ch in enumerate(candidate):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            continue
        try:
            parsed = json.loads(candidate[:end])
            if "title" in parsed and "summary" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

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
