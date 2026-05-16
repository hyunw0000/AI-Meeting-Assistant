"""
pgvector 확장 활성화 및 meeting_embeddings 테이블 생성 마이그레이션.

실행 방법:
    python -m app.migrations.add_pgvector

또는 앱 시작 시 자동 실행 (main.py에서 호출).
"""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import engine, Base

logger = logging.getLogger(__name__)


def run_migration():
    """pgvector 확장 설치 및 임베딩 테이블 생성"""
    with engine.connect() as conn:
        # 1. pgvector 확장 활성화 (슈퍼유저 권한 필요)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector 확장 활성화 완료")
        except Exception as e:
            logger.warning(
                f"pgvector 확장 활성화 실패 (권한 부족 또는 미설치): {e}\n"
                "→ Python 레벨 유사도 검색 fallback 사용"
            )
            conn.rollback()

        # 2. meeting_embeddings 테이블 생성
        try:
            # pgvector가 활성화된 경우: vector 타입 컬럼
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS meeting_embeddings (
                    id           SERIAL PRIMARY KEY,
                    meeting_id   INTEGER NOT NULL UNIQUE
                                 REFERENCES meetings(id) ON DELETE CASCADE,
                    source_text  TEXT,
                    embedding    vector(1024),
                    created_at   TIMESTAMP DEFAULT NOW(),
                    updated_at   TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            logger.info("meeting_embeddings 테이블 생성 완료 (vector 타입)")

        except Exception as e:
            # pgvector 없는 경우: JSON 타입 컬럼 fallback
            logger.warning(f"vector 타입 테이블 생성 실패: {e} → JSON fallback")
            conn.rollback()
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS meeting_embeddings (
                    id           SERIAL PRIMARY KEY,
                    meeting_id   INTEGER NOT NULL UNIQUE
                                 REFERENCES meetings(id) ON DELETE CASCADE,
                    source_text  TEXT,
                    embedding    JSONB,
                    created_at   TIMESTAMP DEFAULT NOW(),
                    updated_at   TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            logger.info("meeting_embeddings 테이블 생성 완료 (JSONB fallback)")

        # 3. HNSW 인덱스 생성 (pgvector가 있는 경우에만 의미 있음)
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS meeting_embeddings_hnsw_idx
                ON meeting_embeddings
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            conn.commit()
            logger.info("HNSW 벡터 인덱스 생성 완료")
        except Exception as e:
            logger.warning(f"HNSW 인덱스 생성 스킵 (pgvector 미지원): {e}")
            conn.rollback()

        # 4. updated_at 자동 갱신 트리거 (선택)
        try:
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """))
            conn.execute(text("""
                DROP TRIGGER IF EXISTS update_meeting_embeddings_updated_at
                ON meeting_embeddings
            """))
            conn.execute(text("""
                CREATE TRIGGER update_meeting_embeddings_updated_at
                BEFORE UPDATE ON meeting_embeddings
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
            """))
            conn.commit()
            logger.info("updated_at 트리거 생성 완료")
        except Exception as e:
            logger.warning(f"트리거 생성 스킵: {e}")
            conn.rollback()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
    print("마이그레이션 완료.")
