# Project Instructions: AI Meeting Assistant

이 파일은 AI Meeting Assistant 프로젝트의 아키텍처, 규칙 및 워크플로우를 정의합니다.

## 🏗️ Architecture Rules
- **Infrastructure:** 하이브리드 구성 (Local Processing + Naver Cloud Platform).
- **Compute:** 로컬 서버(또는 2vCPU, 4GB RAM NCP 서버)와 로컬 LLM 연동.
- **AI Integration:** 
  - 음성 인식(STT): **NCP CLOVA Speech API** 사용.
  - 텍스트 분석 및 요약: **로컬 LLM** (예: Ollama, vLLM) 사용.
  - 일정 관리: **Google Calendar API** 연동을 통해 회의 결과 자동 등록.
- **Database:** **NCP Cloud DB for MySQL** 사용 (데이터 영속성 및 클라우드 관리).

## 🔄 Data Flow (Hybrid Workflow)
1. **Frontend (React):** 사용자가 음성 파일 업로드 및 달력 기반 인터페이스 제공.
2. **Backend (FastAPI):**
   - 파일 수신 및 **NCP CLOVA Speech**로 STT 요청.
   - 변환된 텍스트를 **로컬 LLM**에 전달하여 요약 및 액션 아이템 추출.
   - 최종 데이터를 **NCP Cloud DB (MySQL)**에 저장.
   - **Google Calendar API**를 호출하여 분석된 일정을 사용자 캘린더에 등록.
3. **Security:** API Key, DB 접속 정보, OAuth 인증 정보는 `.env`에서 엄격히 관리.


## 🛠️ Development Workflow
- **API First:** CLOVA API와의 연동을 최우선으로 구현.
- **Structured Data:** HyperCLOVA X 응답은 항상 구조화된 JSON 형식을 지향하여 캘린더 연동 용이성 확보.
- **Security:** API Key 및 DB 접속 정보는 `.env` 파일에서 관리하며 절대 소스 코드에 포함하지 않음.

## 📚 Reference Docs
- NCP CLOVA Speech API 가이드
- NCP CLOVA Studio 가이드
- Google/Naver Calendar API 가이드

항상 한국어로 말해줘
