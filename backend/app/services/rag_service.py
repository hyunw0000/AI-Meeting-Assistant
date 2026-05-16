"""
RAG 유사도 검색 서비스

주요 기능:
1. index_meeting()      - 회의 저장 시 임베딩 생성 & DB 저장
2. search_similar()     - 쿼리 텍스트로 유사 회의 검색
3. reindex_all()        - 기존 모든 회의 재인덱싱
4. delete_embedding()   - 회의 삭제 시 임베딩 제거

pgvector 설치 시:  DB 레벨 코사인 유사도 검색 (빠름, 인덱스 활용)
pgvector 미설치 시: Python 레벨 코사인 유사도 계산 (소규모 개발용)
"""

import logging
from typing import List, Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.embedding import MeetingEmbedding, PGVECTOR_AVAILABLE
from app.models.meeting import Meeting
from app.services.embedding_service import embed_text, cosine_similarity, get_vector_dim

logger = logging.getLogger(__name__)

# 검색 결과 기본값
DEFAULT_TOP_K = 5
DEFAULT_THRESHOLD = 0.3  # 최소 유사도 (0~1)


# ──────────────────────────────────────────────
# 임베딩 대상 텍스트 구성
# ──────────────────────────────────────────────

def _build_source_text(meeting: Meeting) -> str:
    """
    회의 데이터에서 임베딩할 텍스트를 구성한다.
    제목 + 요약 + 트랜스크립트를 합쳐서 의미론적으로 풍부하게 만든다.
    """
    parts = []

    if meeting.title:
        parts.append(f"제목: {meeting.title}")

    if meeting.summary:
        # summary는 이미 구조화된 텍스트 (주제:, 참여자:, ...) → 그대로 사용
        parts.append(f"요약:\n{meeting.summary}")

    if meeting.transcript:
        # 트랜스크립트가 너무 길면 앞 2000자만 사용 (임베딩 모델 토큰 한계 고려)
        transcript_snippet = meeting.transcript[:2000]
        parts.append(f"회의 내용:\n{transcript_snippet}")

    return "\n\n".join(parts)


# ──────────────────────────────────────────────
# 인덱싱 (저장/갱신)
# ──────────────────────────────────────────────

def index_meeting(db: Session, meeting: Meeting) -> MeetingEmbedding:
    """
    단일 회의를 임베딩하여 DB에 저장.
    이미 임베딩이 있으면 갱신(upsert).
    """
    source_text = _build_source_text(meeting)
    vector = embed_text(source_text)

    # 기존 임베딩 조회 (upsert)
    existing = (
        db.query(MeetingEmbedding)
        .filter(MeetingEmbedding.meeting_id == meeting.id)
        .first()
    )

    if existing:
        existing.source_text = source_text
        existing.embedding = vector
        db.commit()
        db.refresh(existing)
        logger.info(f"임베딩 갱신 완료: meeting_id={meeting.id}")
        return existing
    else:
        emb = MeetingEmbedding(
            meeting_id=meeting.id,
            source_text=source_text,
            embedding=vector,
        )
        db.add(emb)
        db.commit()
        db.refresh(emb)
        logger.info(f"임베딩 생성 완료: meeting_id={meeting.id}")
        return emb


def delete_embedding(db: Session, meeting_id: int) -> bool:
    """회의 삭제 시 임베딩도 제거 (CASCADE가 없는 환경 대비)"""
    emb = (
        db.query(MeetingEmbedding)
        .filter(MeetingEmbedding.meeting_id == meeting_id)
        .first()
    )
    if emb:
        db.delete(emb)
        db.commit()
        return True
    return False


def reindex_all(db: Session) -> dict:
    """DB에 있는 모든 회의를 재임베딩 (관리자용)"""
    meetings = db.query(Meeting).all()
    success, failed = 0, 0

    for meeting in meetings:
        try:
            index_meeting(db, meeting)
            success += 1
        except Exception as e:
            logger.error(f"재인덱싱 실패 meeting_id={meeting.id}: {e}")
            failed += 1

    return {"total": len(meetings), "success": success, "failed": failed}


# ──────────────────────────────────────────────
# 유사도 검색
# ──────────────────────────────────────────────

def search_similar(
    db: Session,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    threshold: float = DEFAULT_THRESHOLD,
    meeting_id_exclude: Optional[int] = None,
) -> List[dict]:
    """
    쿼리 텍스트와 유사한 회의를 검색하여 반환.

    Args:
        db: SQLAlchemy 세션
        query: 검색할 자연어 쿼리
        top_k: 반환할 최대 결과 수
        threshold: 최소 코사인 유사도 (0.0~1.0)
        meeting_id_exclude: 제외할 meeting_id (현재 보고 있는 회의 제외용)

    Returns:
        [
          {
            "meeting_id": int,
            "title": str,
            "date": str,
            "summary": str,
            "similarity": float,
            "matched_snippet": str,
          },
          ...
        ]
    """
    if not query or not query.strip():
        return []

    query_vector = embed_text(query)

    if PGVECTOR_AVAILABLE:
        return _search_pgvector(db, query_vector, top_k, threshold, meeting_id_exclude)
    else:
        return _search_python(db, query_vector, top_k, threshold, meeting_id_exclude)


# ──────────────────────────────────────────────
# pgvector 방식 (DB 레벨 검색)
# ──────────────────────────────────────────────

def _search_pgvector(
    db: Session,
    query_vector: List[float],
    top_k: int,
    threshold: float,
    exclude_id: Optional[int],
) -> List[dict]:
    """
    pgvector의 <=> 연산자(코사인 거리)를 사용한 DB 레벨 검색.
    코사인 거리 = 1 - 코사인 유사도 이므로 변환 필요.
    """
    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

    exclude_clause = ""
    params: dict = {"vector": vector_str, "threshold": 1 - threshold, "top_k": top_k}

    if exclude_id is not None:
        exclude_clause = "AND me.meeting_id != :exclude_id"
        params["exclude_id"] = exclude_id

    sql = text(f"""
        SELECT
            m.id            AS meeting_id,
            m.title         AS title,
            m.date          AS date,
            m.summary       AS summary,
            me.source_text  AS source_text,
            (1 - (me.embedding <=> CAST(:vector AS vector))) AS similarity
        FROM meeting_embeddings me
        JOIN meetings m ON m.id = me.meeting_id
        WHERE me.embedding IS NOT NULL
          AND (1 - (me.embedding <=> CAST(:vector AS vector))) >= (1 - :threshold)
          {exclude_clause}
        ORDER BY me.embedding <=> CAST(:vector AS vector)
        LIMIT :top_k
    """)

    rows = db.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


# ──────────────────────────────────────────────
# Python 레벨 fallback 검색
# ──────────────────────────────────────────────

def _search_python(
    db: Session,
    query_vector: List[float],
    top_k: int,
    threshold: float,
    exclude_id: Optional[int],
) -> List[dict]:
    """
    pgvector 없이 Python numpy로 코사인 유사도 계산.
    임베딩 수가 적은 개발 환경에서 사용.
    """
    q = db.query(MeetingEmbedding, Meeting).join(
        Meeting, Meeting.id == MeetingEmbedding.meeting_id
    )
    if exclude_id is not None:
        q = q.filter(MeetingEmbedding.meeting_id != exclude_id)

    rows = q.all()

    scored = []
    for emb, meeting in rows:
        if emb.embedding is None:
            continue
        sim = cosine_similarity(query_vector, emb.embedding)
        if sim >= threshold:
            scored.append((sim, emb, meeting))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for sim, emb, meeting in scored[:top_k]:
        results.append({
            "meeting_id": meeting.id,
            "title": meeting.title or "제목 없음",
            "date": meeting.date.strftime("%Y-%m-%d") if meeting.date else None,
            "summary": meeting.summary or "",
            "similarity": round(float(sim), 4),
            "matched_snippet": _extract_snippet(emb.source_text or "", 200),
        })

    return results


# ──────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    """SQLAlchemy Row → dict 변환"""
    source_text = row.source_text or ""
    return {
        "meeting_id": row.meeting_id,
        "title": row.title or "제목 없음",
        "date": row.date.strftime("%Y-%m-%d") if row.date else None,
        "summary": row.summary or "",
        "similarity": round(float(row.similarity), 4),
        "matched_snippet": _extract_snippet(source_text, 200),
    }


def _extract_snippet(text: str, max_len: int = 200) -> str:
    """긴 텍스트에서 요약 스니펫 추출"""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def get_embedding_status(db: Session) -> dict:
    """임베딩 현황 조회 (관리자용)"""
    total_meetings = db.query(Meeting).count()
    total_embeddings = db.query(MeetingEmbedding).count()
    unindexed = total_meetings - total_embeddings

    return {
        "pgvector_available": PGVECTOR_AVAILABLE,
        "vector_dim": get_vector_dim(),
        "total_meetings": total_meetings,
        "indexed_meetings": total_embeddings,
        "unindexed_meetings": max(unindexed, 0),
    }
