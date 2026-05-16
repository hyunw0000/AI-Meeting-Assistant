from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
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
    memo = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # RAG 임베딩 (1:1)
    embedding = relationship(
        "MeetingEmbedding",
        back_populates="meeting",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
