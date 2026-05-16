"""
RAG 유사도 검색 API 라우터

엔드포인트:
    POST /api/v1/rag/search          - 자연어 쿼리로 유사 회의 검색
    POST /api/v1/rag/index/{id}      - 특정 회의 임베딩 생성/갱신
    POST /api/v1/rag/reindex         - 전체 회의 재인덱싱 (관리자)
    DELETE /api/v1/rag/index/{id}    - 특정 회의 임베딩 삭제
    GET  /api/v1/rag/status          - 임베딩 현황 조회
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.meeting import Meeting
from app.services.rag_service import (
    search_similar,
    index_meeting,
    delete_embedding,
    reindex_all,
    get_embedding_status,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG Search"])


# ──────────────────────────────────────────────
# Pydantic 스키마
# ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="검색할 자연어 쿼리")
    top_k: int = Field(default=5, ge=1, le=20, description="반환할 최대 결과 수")
    threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="최소 코사인 유사도 (0~1)")
    exclude_meeting_id: Optional[int] = Field(default=None, description="제외할 meeting_id")


class SearchResultItem(BaseModel):
    meeting_id: int
    title: str
    date: Optional[str]
    summary: str
    similarity: float
    matched_snippet: str


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[SearchResultItem]


class IndexResponse(BaseModel):
    success: bool
    meeting_id: int
    message: str


class ReindexResponse(BaseModel):
    success: bool
    total: int
    indexed: int
    failed: int


class StatusResponse(BaseModel):
    pgvector_available: bool
    vector_dim: int
    total_meetings: int
    indexed_meetings: int
    unindexed_meetings: int


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
def search_meetings(
    body: SearchRequest,
    db: Session = Depends(get_db),
):
    """
    자연어 쿼리로 유사한 회의를 검색합니다.

    - 쿼리를 임베딩 벡터로 변환 후 코사인 유사도 기반으로 상위 K개 회의를 반환
    - pgvector 설치 시 DB 레벨 검색, 미설치 시 Python 레벨 검색
    - threshold 이상인 결과만 반환

    예시:
        {"query": "마케팅 캠페인 관련 회의", "top_k": 5, "threshold": 0.3}
    """
    try:
        results = search_similar(
            db=db,
            query=body.query,
            top_k=body.top_k,
            threshold=body.threshold,
            meeting_id_exclude=body.exclude_meeting_id,
        )
        return SearchResponse(
            query=body.query,
            count=len(results),
            results=[SearchResultItem(**r) for r in results],
        )
    except Exception as e:
        logger.error(f"유사도 검색 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/search", response_model=SearchResponse)
def search_meetings_get(
    q: str = Query(..., min_length=1, description="검색 쿼리"),
    top_k: int = Query(default=5, ge=1, le=20),
    threshold: float = Query(default=0.3, ge=0.0, le=1.0),
    exclude: Optional[int] = Query(default=None, description="제외할 meeting_id"),
    db: Session = Depends(get_db),
):
    """
    GET 방식 검색 (프론트엔드 간편 호출용).

    예시: GET /api/v1/rag/search?q=마케팅&top_k=3
    """
    try:
        results = search_similar(
            db=db,
            query=q,
            top_k=top_k,
            threshold=threshold,
            meeting_id_exclude=exclude,
        )
        return SearchResponse(
            query=q,
            count=len(results),
            results=[SearchResultItem(**r) for r in results],
        )
    except Exception as e:
        logger.error(f"유사도 검색 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.post("/index/{meeting_id}", response_model=IndexResponse)
def index_single_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
):
    """
    특정 회의의 임베딩을 생성하거나 갱신합니다.
    이미 임베딩이 존재하면 덮어씁니다 (upsert).
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise HTTPException(status_code=404, detail=f"회의 ID {meeting_id}를 찾을 수 없습니다.")

    try:
        index_meeting(db, meeting)
        return IndexResponse(
            success=True,
            meeting_id=meeting_id,
            message=f"회의 ID {meeting_id} 임베딩 완료",
        )
    except Exception as e:
        logger.error(f"임베딩 생성 실패 meeting_id={meeting_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"임베딩 생성 실패: {str(e)}")


@router.delete("/index/{meeting_id}", response_model=IndexResponse)
def delete_meeting_embedding(
    meeting_id: int,
    db: Session = Depends(get_db),
):
    """특정 회의의 임베딩 데이터를 삭제합니다."""
    deleted = delete_embedding(db, meeting_id)
    return IndexResponse(
        success=deleted,
        meeting_id=meeting_id,
        message="임베딩 삭제 완료" if deleted else "임베딩 없음 (이미 삭제됨)",
    )


@router.post("/reindex", response_model=ReindexResponse)
def reindex_all_meetings(db: Session = Depends(get_db)):
    """
    DB에 있는 모든 회의를 재임베딩합니다.
    임베딩 모델이 변경되었거나 벡터 차원이 바뀐 경우 실행하세요.
    ⚠️ 회의 수가 많으면 시간이 오래 걸릴 수 있습니다.
    """
    try:
        result = reindex_all(db)
        return ReindexResponse(
            success=result["failed"] == 0,
            total=result["total"],
            indexed=result["success"],
            failed=result["failed"],
        )
    except Exception as e:
        logger.error(f"전체 재인덱싱 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"재인덱싱 실패: {str(e)}")


@router.get("/status", response_model=StatusResponse)
def embedding_status(db: Session = Depends(get_db)):
    """
    임베딩 시스템 현황을 반환합니다.
    - pgvector 설치 여부, 벡터 차원, 인덱싱된 회의 수 등
    """
    try:
        status = get_embedding_status(db)
        return StatusResponse(**status)
    except Exception as e:
        logger.error(f"상태 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
