import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import engine, Base, get_db
from app.api import calendar, meetings
from app.api import rag  # RAG 검색 라우터

# 모델 임포트 순서 중요: Meeting → MeetingEmbedding (FK 의존성)
from app.models import Meeting, MeetingEmbedding  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Meeting Assistant",
    description="회의 음성 업로드 → STT → LLM 요약 → RAG 유사도 검색 서비스",
    version="1.1.0",
)

# DB 테이블 생성 (기존 테이블 유지, 신규 테이블 추가)
Base.metadata.create_all(bind=engine)

# pgvector 확장 및 임베딩 테이블 마이그레이션
try:
    from app.migrations.add_pgvector import run_migration
    run_migration()
    logger.info("pgvector 마이그레이션 완료")
except Exception as e:
    logger.warning(f"pgvector 마이그레이션 스킵: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://101.79.22.220.nip.io",
        "http://101.79.22.220"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calendar.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")  # RAG 검색


@app.get("/")
async def root():
    return {"message": "Welcome to AI Meeting Assistant API"}


@app.get("/db-test")
def test_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "Successfully connected to DB"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
