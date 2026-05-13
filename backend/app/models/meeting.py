from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from app.core.database import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    date = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text)
    action_items = Column(JSON)  # Store as a list in JSON
    transcript = Column(Text)
    file_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
