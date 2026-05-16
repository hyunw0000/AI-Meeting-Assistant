"""
벡터 임베딩 저장 모델.
pgvector 확장이 필요합니다: CREATE EXTENSION IF NOT EXISTS vector;

Meeting 1:1 관계로 연결 - 회의 삭제 시 임베딩도 cascade 삭제.
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

try:
    # pgvector SQLAlchemy 타입 (pgvector 패키지 설치 시)
    from pgvector.sqlalchemy import Vector
    _PGVECTOR_AVAILABLE = True
except ImportError:
    # pgvector 미설치 시 JSON 컬럼으로 대체 (개발용)
    from sqlalchemy import JSON
    Vector = None
    _PGVECTOR_AVAILABLE = False


def _vector_column(dim: int):
    """pgvector 설치 여부에 따라 적절한 컬럼 타입 반환"""
    if _PGVECTOR_AVAILABLE and Vector is not None:
        return Column(Vector(dim), nullable=True)
    else:
        # 개발/테스트 환경: JSON 배열로 저장 (유사도 검색은 Python 레벨에서 수행)
        return Column(JSON, nullable=True)


class MeetingEmbedding(Base):
    __tablename__ = "meeting_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    # Meeting 외래키 (cascade delete)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # 임베딩 대상 텍스트 (어떤 내용을 임베딩했는지 기록)
    source_text = Column(Text, nullable=True)

    # 벡터 (pgvector: Vector 타입 / fallback: JSON)
    embedding = _vector_column(dim=1024)

    # 임베딩 생성 시각
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    meeting = relationship("Meeting", back_populates="embedding")

    def __repr__(self):
        return f"<MeetingEmbedding meeting_id={self.meeting_id}>"


PGVECTOR_AVAILABLE = _PGVECTOR_AVAILABLE
