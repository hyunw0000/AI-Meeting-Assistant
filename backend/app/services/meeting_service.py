from datetime import datetime, timedelta
import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:1.5b"


def generate_meeting_result(transcript):
    if not transcript:
        return fallback_result("")

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
      "due_date": "YYYY-MM-DD 또는 null"
    }}
  ]
}}

규칙:
- 설명 문장 없이 JSON만 반환해.
- 마감일이 없으면 due_date는 null로 해.
- 담당자가 없으면 assignee는 "미정"으로 해.
- 날짜 표현은 가능한 YYYY-MM-DD로 변환해.
- 오늘 날짜 기준은 {datetime.now().date().isoformat()}야.
- "내일"은 오늘 날짜 기준 다음 날로 변환해.

회의 텍스트:
{transcript}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        result = response.json()
        content = result.get("response", "")

        parsed_result = parse_llm_json(content, transcript)

        parsed_result["tasks"] = fix_due_dates(
            parsed_result.get("tasks", []),
            transcript
        )

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


def fix_due_dates(tasks, transcript):
    today = datetime.now().date()

    for task in tasks:
        due_date = task.get("due_date")

        if due_date and due_date != "null":
            continue

        if "내일" in transcript:
            task["due_date"] = (today + timedelta(days=1)).isoformat()

        elif "모레" in transcript:
            task["due_date"] = (today + timedelta(days=2)).isoformat()

        elif "오늘" in transcript:
            task["due_date"] = today.isoformat()

        else:
            match = re.search(r"(\d{1,2})월\s*(\d{1,2})일", transcript)

            if match:
                month = int(match.group(1))
                day = int(match.group(2))

                task["due_date"] = datetime(
                    today.year,
                    month,
                    day
                ).date().isoformat()

    return tasks