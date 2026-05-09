# Project Instructions: AI Meeting Assistant

이 파일은 AI Meeting Assistant 프로젝트의 아키텍처, 규칙 및 워크플로우를 정의합니다.

## 🏗️ Architecture Rules
- **Infrastructure:** **Naver Cloud Platform (NCP)** 기반 인프라 구성.
- **Compute:** NCP 서버 (2vCPU, 4GB RAM)에서 Web Server(FastAPI), RAG, 로컬 LLM(llama.cpp) 구동.
- **AI Integration (Pipeline):**
  1. **STT (Speech-to-Text):** **NCP CLOVA Speech API**를 사용하며, **비동기 파일 분석**과 **실시간 스트리밍 인식**을 모두 지원.
  2. **RAG (Vector Store):** 텍스트 데이터를 벡터화하여 저장 및 회의 문맥 검색 (FAISS/ChromaDB).
  3. **LLM (Summary/Analysis):** **llama.cpp + Qwen (GGUF)**를 활용하여 요약 및 액션 아이템 추출.
  4. **Automation:** **Google Calendar API**를 활용한 일정 자동 등록.
- **Database:** **NCP Cloud DB for MySQL**을 사용하여 회의록, 요약 결과, 일정 정보 관리.

## 🔄 Dual-Mode Data Flow

### Mode 1: 실시간 회의 기록 (Streaming Mode)
1. **Streaming:** 사용자가 마이크 권한을 허용하고 '녹음 시작' 시, 브라우저가 음성 조각(Chunk)을 **WebSocket**을 통해 백엔드로 실시간 전송.
2. **Real-time STT:** 백엔드(FastAPI)는 받은 조각을 **NCP CLOVA Speech Streaming API**로 즉시 릴레이하고 변환된 텍스트를 다시 프런트엔드에 실시간 출력.
3. **Auto-Save:** 스트리밍 중 백엔드는 수신된 음성 조각들을 합쳐 서버 내 **완전한 음성 파일로 자동 저장**.
4. **Post-Process:** 회의 종료 시, 전체 텍스트와 저장된 파일을 기반으로 RAG 분석 및 LLM 요약 단계로 자동 진입.

### Mode 2: 기존 파일 분석 (Upload Mode)
1. **Upload:** 사용자가 이미 녹음된 파일을 업로드.
2. **Batch STT:** **NCP CLOVA Speech 비동기 API**를 호출하여 전체 스크립트 획득.

### 공통 후속 단계 (RAG & Analysis)
1. **Indexing:** 추출된 전체 텍스트를 벡터 DB에 인덱싱.
2. **Reasoning:** **로컬 LLM(Qwen)**이 검색된 문맥을 바탕으로 요약 및 캘린더 등록용 JSON 생성.
3. **Action:** Google Calendar 등록 및 MySQL 결과 저장.

## 🛠️ Security & Optimization
- **API Key Management:** CLOVA Speech(Secret Key, Streaming URL), Google OAuth, DB 접속 정보는 `.env`에서 엄격히 관리.
- **WebSocket Stability:** 실시간 모드에서 네트워크 불안정을 고려한 재연결 및 버퍼링 전략 수립.
- **Resource Management:** 4GB RAM 환경을 고려하여 **4-bit 양자화 모델** 사용 및 불필요한 메모리 점유 최소화.

## 📚 Reference Docs
- NCP CLOVA Speech API (Streaming/Async) 가이드
- Google Calendar API / OAuth 2.0 가이드
- llama.cpp & Qwen Documentation
- NCP Cloud DB for MySQL 가이드

항상 한국어로 말해줘
