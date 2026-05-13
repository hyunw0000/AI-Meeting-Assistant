from app.core.config import settings
import requests

def test_clova_connection():
    print("--- 환경 변수 확인 ---")
    print(f"URL: {settings.CLOVA_SPEECH_INVOKE_URL}")
    # 키의 앞부분만 출력하여 보안 유지
    mask_key = settings.CLOVA_SPEECH_SECRET_KEY[:5] + "***" if settings.CLOVA_SPEECH_SECRET_KEY else "None"
    print(f"Key loaded: {mask_key}")
    
    print("\n--- API 연결 테스트 ---")
    # API 요청 URL 확인 (CLOVA Speech 기본 호출 형태)
    url = f"{settings.CLOVA_SPEECH_INVOKE_URL}/recognizer/object-storage"
    headers = {
        "X-CLOVASPEECH-API-KEY": settings.CLOVA_SPEECH_SECRET_KEY
    }
    
    try:
        # 인증 오류를 확인하기 위해 간단한 요청 시도
        # 인증이 제대로 되면 400(Bad Request) 혹은 200이 나오며, 인증 실패 시 401/403이 나옵니다.
        response = requests.post(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code in [401, 403]:
            print("❌ 인증 실패: API Key가 잘못되었거나 서버 접근 권한이 없습니다.")
        elif response.status_code == 404:
            print("⚠️ 연결은 되었으나 URL 경로가 잘못되었습니다 (404).")
        else:
            print("✅ API 인증 성공 (서버로부터 응답을 받았습니다)")
    except Exception as e:
        print(f"에러 발생 (네트워크/설정 확인 필요): {e}")

if __name__ == "__main__":
    test_clova_connection()
