import requests
import json
import time
import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

CLOVA_SPEECH_INVOKE_URL = os.getenv("CLOVA_SPEECH_INVOKE_URL")
CLOVA_SPEECH_SECRET_KEY = os.getenv("CLOVA_SPEECH_SECRET_KEY")

print(f"DEBUG: URL={CLOVA_SPEECH_INVOKE_URL}, KEY={CLOVA_SPEECH_SECRET_KEY}")

headers = {
    "Accept": "application/json;UTF-8",
    "X-CLOVASPEECH-API-KEY": CLOVA_SPEECH_SECRET_KEY
}

def speech_to_text(file_path):
    print(f"DEBUG: STT 분석 시작! 파일 경로: {file_path}, 존재여부: {os.path.exists(file_path)}")
    
    if not os.path.exists(file_path):
        return "파일을 찾을 수 없음"

    request_body = {
        "language": "ko-KR",
        "completion": "sync"
    }

    try:
        with open(file_path, "rb") as f:
            files = {
                "media": f,
                "params": (
                    None,
                    json.dumps(request_body).encode("UTF-8"),
                    "application/json"
                )
            }

            response = requests.post(
                CLOVA_SPEECH_INVOKE_URL + "/recognizer/upload",
                headers=headers,
                files=files
            )
            
            print(f"DEBUG: API 응답 상태코드: {response.status_code}")
            result = response.json()
            print(f"DEBUG: API 응답 결과: {result}")
            
            if "text" in result:
                return result["text"]
            return "STT 변환 실패"
    except Exception as e:
        print(f"DEBUG: STT 분석 중 오류 발생: {e}")
        return f"STT 분석 오류: {str(e)}"