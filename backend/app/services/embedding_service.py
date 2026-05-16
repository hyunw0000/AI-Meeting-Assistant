"""
임베딩 서비스
- 우선순위 1: LLM 서버(10.0.30.6:8001)의 /embed 엔드포인트
- 우선순위 2: sentence-transformers 로컬 모델 (fallback)
- 우선순위 3: TF-IDF 기반 더미 벡터 (개발/테스트용 최후 fallback)
"""

import os
import hashlib
import logging
from typing import List

import requests
import numpy as np

logger = logging.getLogger(__name__)

# LLM 서버 엔드포인트
LLM_SERVER_BASE = os.getenv("LLM_SERVER_URL", "http://10.0.30.6:8001")
EMBED_ENDPOINT = f"{LLM_SERVER_BASE}/embed"
EMBED_TIMEOUT = int(os.getenv("EMBED_TIMEOUT", "30"))

# 벡터 차원: LLM 서버 모델에 맞게 조정 가능
VECTOR_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))


# ──────────────────────────────────────────────
# 내부 fallback: sentence-transformers
# ──────────────────────────────────────────────
_st_model = None

def _get_st_model():
    """sentence-transformers 모델 lazy-load (설치된 경우에만)"""
    global _st_model
    if _st_model is not None:
        return _st_model
    try:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv(
            "ST_MODEL_NAME",
            "snunlp/KR-ELECTRA-discriminator"  # 한국어 특화 소형 모델
        )
        logger.info(f"sentence-transformers 모델 로드: {model_name}")
        _st_model = SentenceTransformer(model_name)
        return _st_model
    except ImportError:
        logger.warning("sentence-transformers 미설치. TF-IDF fallback 사용.")
        return None
    except Exception as e:
        logger.warning(f"sentence-transformers 로드 실패: {e}")
        return None


def _tfidf_vector(text: str, dim: int = VECTOR_DIM) -> List[float]:
    """
    sentence-transformers도 없을 때 쓰는 결정론적 해시 기반 의사(pseudo) 벡터.
    실제 의미 유사도는 없지만, 같은 텍스트는 항상 같은 벡터를 반환한다.
    개발/단위테스트 환경에서만 사용.
    """
    import struct

    tokens = text.lower().split()
    vec = [0.0] * dim
    for token in tokens:
        digest = hashlib.md5(token.encode()).digest()
        for i in range(0, min(16, dim * 4), 4):
            idx = struct.unpack_from("<I", digest, i)[0] % dim
            vec[idx] += 1.0

    norm = (sum(v ** 2 for v in vec) ** 0.5) or 1.0
    return [v / norm for v in vec]


# ──────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────

def embed_text(text: str) -> List[float]:
    """
    텍스트 → 임베딩 벡터 (float list).
    서버 → ST 모델 → TF-IDF 순으로 시도.
    """
    if not text or not text.strip():
        return [0.0] * VECTOR_DIM

    # 1) LLM 서버 호출
    try:
        resp = requests.post(
            EMBED_ENDPOINT,
            json={"text": text},
            timeout=EMBED_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            vector = data.get("embedding") or data.get("vector") or data.get("data")
            if isinstance(vector, list) and len(vector) > 0:
                logger.debug(f"LLM 서버 임베딩 성공 (dim={len(vector)})")
                return _pad_or_trim(vector, VECTOR_DIM)
        logger.warning(f"LLM 서버 embed 응답 이상: status={resp.status_code}")
    except requests.exceptions.ConnectionError:
        logger.warning("LLM 서버 연결 실패 → sentence-transformers fallback")
    except requests.exceptions.Timeout:
        logger.warning("LLM 서버 embed 타임아웃 → sentence-transformers fallback")
    except Exception as e:
        logger.warning(f"LLM 서버 embed 오류: {e}")

    # 2) sentence-transformers fallback
    model = _get_st_model()
    if model is not None:
        try:
            vector = model.encode(text, normalize_embeddings=True).tolist()
            logger.debug(f"sentence-transformers 임베딩 성공 (dim={len(vector)})")
            return _pad_or_trim(vector, VECTOR_DIM)
        except Exception as e:
            logger.warning(f"sentence-transformers 실패: {e}")

    # 3) TF-IDF 더미 벡터 (최후 수단)
    logger.warning("TF-IDF 더미 벡터 사용 (의미 유사도 없음)")
    return _tfidf_vector(text, VECTOR_DIM)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """여러 텍스트를 배치로 임베딩 (배치 전송 지원)"""
    if not texts:
        return []

    # 1) LLM 서버 배치 엔드포인트 시도
    try:
        resp = requests.post(
            f"{LLM_SERVER_BASE}/embed/batch",
            json={"texts": texts},
            timeout=EMBED_TIMEOUT * len(texts),
        )
        if resp.status_code == 200:
            data = resp.json()
            vectors = data.get("embeddings") or data.get("vectors")
            if isinstance(vectors, list) and len(vectors) == len(texts):
                return [_pad_or_trim(v, VECTOR_DIM) for v in vectors]
    except Exception:
        pass

    # 2) 개별 호출 fallback
    return [embed_text(t) for t in texts]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """두 벡터 간 코사인 유사도 (Python 레벨 - DB 없이 테스트용)"""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _pad_or_trim(vector: List[float], target_dim: int) -> List[float]:
    """벡터 차원을 target_dim에 맞게 패딩/트리밍"""
    if len(vector) == target_dim:
        return vector
    if len(vector) > target_dim:
        return vector[:target_dim]
    return vector + [0.0] * (target_dim - len(vector))


def get_vector_dim() -> int:
    return VECTOR_DIM
