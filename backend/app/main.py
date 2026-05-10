from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.database import engine, Base, get_db
from app.models import meeting
from app.api import calendar

# DB 테이블 생성 - DB 연결이 안 될 경우 서버가 멈추므로 일시적으로 주석 처리
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Meeting Assistant")

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React 기본 포트 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(calendar.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to AI Meeting Assistant API connected to NCP DB"}

@app.get("/db-test")
def test_db(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "success", "message": "Successfully connected to NCP MySQL"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
