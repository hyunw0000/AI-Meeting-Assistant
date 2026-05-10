from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api import calendar, meetings

app = FastAPI(title="AI Meeting Assistant")

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
