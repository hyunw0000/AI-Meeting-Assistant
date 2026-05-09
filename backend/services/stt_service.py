import requests
import json
import time
import os

from dotenv import load_dotenv

load_dotenv()

CLOVA_SPEECH_INVOKE_URL = os.getenv("CLOVA_SPEECH_INVOKE_URL")
CLOVA_SPEECH_SECRET_KEY = os.getenv("CLOVA_SPEECH_SECRET_KEY")

headers = {
    "Accept": "application/json;UTF-8",
    "X-CLOVASPEECH-API-KEY": CLOVA_SPEECH_SECRET_KEY
}

def speech_to_text(file_path):

    request_body = {
        "language": "ko-KR",
        "completion": "sync"
    }

    files = {
        "media": open(file_path, "rb"),
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

    result = response.json()

    print(result)

    if "text" in result:
        return result["text"]

    return "STT 변환 실패"