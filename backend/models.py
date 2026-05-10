from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON

from database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(String(50), unique=True, index=True)

    source = Column(String(30))
    original_filename = Column(String(255))
    saved_filename = Column(String(255))
    file_path = Column(String(500))

    meeting_date = Column(String(20), index=True)
    transcript = Column(Text)
    meeting_result = Column(JSON)

    created_at = Column(DateTime, default=datetime.now)