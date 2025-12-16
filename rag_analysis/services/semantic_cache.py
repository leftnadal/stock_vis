"""
Semantic Cache Service - 시맨틱 캐시 서비스

유사한 질문에 대해 과거 분석 결과를 재사용하여 비용과 응답 시간을 절감합니다.
"""

import uuid
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sentence_transformers import SentenceTransformer
from django.conf import settings

from .neo4j_driver import get_neo4j_driver

logger = logging.getLogger(__name__)


class SemanticCacheService:
    """
    시맨틱 캐시 서비스

    Features:
        - 질문 임베딩 기반 유사도 검색
        - 엔티티 매칭 점수 결합
        - TTL 기반 캐시 만료
        - 캐시 히트 카운터
    """

    # 임베딩 모델 (384차원)
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    # 캐시 설정
    SIMILARITY_THRESHOLD = 0.85  # 유사도 임계값
    ENTITY_WEIGHT = 0.4  # 엔티티 매칭 가중치
    SEMANTIC_WEIGHT = 0.6  # 시맨틱 유사도 가중치
    FINAL_THRESHOLD = 0.70  # 최종 점수 임계값
    CACHE_TTL_DAYS = 7  # 캐시 유효 기간

    _encoder: Optional[SentenceTransformer] = None

    def __init__(self):
        """인스턴스 초기화 (인코더는 지연 로딩)"""
        pass

    @property
    def encoder(self) -> Optional[SentenceTransformer]:
        """임베딩 인코더 (지연 로딩)"""
        if SemanticCacheService._encoder is None:
            try:
                SemanticCacheService._encoder = SentenceTransformer(self.EMBEDDING_MODEL)
                logger.info(f"Loaded embedding model: {self.EMBEDDING_MODEL}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                return None
        return SemanticCacheService._encoder

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        텍스트를 벡터로 변환

        Args:
            text: 입력 텍스트

        Returns:
            384차원 벡터 또는 None
        """
        if self.encoder is None:
            return None

        try:
            embedding = self.encoder.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    async def find_similar(
        self,
        question: str,
        entities: List[str],
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        유사한 과거 분석 검색

        Args:
            question: 사용자 질문
            entities: 추출된 엔티티 리스트 (종목 심볼 등)
            user_id: 사용자 ID (선택, 개인화 캐시용)

        Returns:
            캐시 히트 시:
            {
                'cache_hit': True,
                'cache_id': str,
                'response': str,
                'suggestions': list,
                'similarity_score': float,
                'entity_match_score': float,
                'final_score': float,
                'created_at': str,
                'hit_count': int
            }
            캐시 미스 시: None
        """
        driver = get_neo4j_driver()
        if driver is None:
            logger.warning("Neo4j unavailable - cache disabled")
            return None

        # 질문 임베딩 생성
        embedding = self._get_embedding(question)
        if embedding is None:
            logger.warning("Failed to generate embedding - cache disabled")
            return None

        try:
            with driver.session(database=settings.NEO4J_DATABASE) as session:
                # 벡터 유사도 검색 + 엔티티 매칭
                result = session.run("""
                    CALL db.index.vector.queryNodes(
                        'analysis_question_embedding', 10, $embedding
                    ) YIELD node as cache, score
                    WHERE score >= $threshold
                      AND cache.expires_at > datetime()

                    // 엔티티 매칭 (관련 종목)
                    OPTIONAL MATCH (cache)-[:ANALYZED]->(stock:Stock)
                    WHERE stock.symbol IN $entities
                    WITH cache, score, count(stock) as entity_matches

                    // 최종 점수 계산: semantic * 0.6 + entity_match * 0.4
                    WITH cache,
                         score * $semantic_weight +
                         (toFloat(entity_matches) / CASE WHEN size($entities) > 0 THEN size($entities) ELSE 1 END) * $entity_weight
                         as final_score,
                         score as similarity_score,
                         toFloat(entity_matches) / CASE WHEN size($entities) > 0 THEN size($entities) ELSE 1 END as entity_score

                    WHERE final_score >= $final_threshold

                    ORDER BY final_score DESC
                    LIMIT 1

                    // 히트 카운터 증가
                    SET cache.hit_count = coalesce(cache.hit_count, 0) + 1,
                        cache.last_hit_at = datetime()

                    RETURN
                        cache.cache_id as cache_id,
                        cache.question as original_question,
                        cache.response as response,
                        cache.suggestions as suggestions,
                        cache.created_at as created_at,
                        cache.hit_count as hit_count,
                        similarity_score,
                        entity_score,
                        final_score
                """, {
                    'embedding': embedding,
                    'threshold': self.SIMILARITY_THRESHOLD,
                    'entities': entities or [],
                    'semantic_weight': self.SEMANTIC_WEIGHT,
                    'entity_weight': self.ENTITY_WEIGHT,
                    'final_threshold': self.FINAL_THRESHOLD
                })

                record = result.single()

                if record:
                    logger.info(
                        f"Cache HIT: score={record['final_score']:.3f}, "
                        f"hit_count={record['hit_count']}"
                    )

                    # suggestions JSON 파싱
                    suggestions_raw = record['suggestions']
                    if isinstance(suggestions_raw, str):
                        try:
                            suggestions = json.loads(suggestions_raw)
                        except json.JSONDecodeError:
                            suggestions = []
                    else:
                        suggestions = suggestions_raw or []

                    return {
                        'cache_hit': True,
                        'cache_id': record['cache_id'],
                        'original_question': record['original_question'],
                        'response': record['response'],
                        'suggestions': suggestions,
                        'similarity_score': record['similarity_score'],
                        'entity_match_score': record['entity_score'],
                        'final_score': record['final_score'],
                        'created_at': str(record['created_at']),
                        'hit_count': record['hit_count']
                    }

                logger.debug("Cache MISS: no similar question found")
                return None

        except Exception as e:
            logger.error(f"Semantic cache lookup failed: {e}")
            return None

    async def store(
        self,
        question: str,
        entities: List[str],
        response: str,
        suggestions: List[Dict[str, str]],
        usage: Dict[str, int],
        user_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> Optional[str]:
        """
        분석 결과 캐시 저장

        Args:
            question: 사용자 질문
            entities: 관련 엔티티 (종목 심볼 등)
            response: LLM 응답
            suggestions: 제안 종목 리스트
            usage: 토큰 사용량 {'input_tokens': int, 'output_tokens': int}
            user_id: 사용자 ID (선택)
            session_id: 세션 ID (선택)

        Returns:
            cache_id (성공 시) 또는 None
        """
        driver = get_neo4j_driver()
        if driver is None:
            logger.warning("Neo4j unavailable - cannot store cache")
            return None

        # 질문 임베딩 생성
        embedding = self._get_embedding(question)
        if embedding is None:
            logger.warning("Failed to generate embedding - cannot store cache")
            return None

        cache_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=self.CACHE_TTL_DAYS)

        try:
            with driver.session(database=settings.NEO4J_DATABASE) as session:
                # 캐시 노드 생성
                # suggestions를 JSON 문자열로 변환 (Neo4j는 Map 타입 프로퍼티 미지원)
                suggestions_json = json.dumps(suggestions, ensure_ascii=False)

                session.run("""
                    CREATE (c:AnalysisCache {
                        cache_id: $cache_id,
                        question: $question,
                        question_embedding: $embedding,
                        response: $response,
                        suggestions: $suggestions,
                        input_tokens: $input_tokens,
                        output_tokens: $output_tokens,
                        user_id: $user_id,
                        session_id: $session_id,
                        created_at: datetime(),
                        expires_at: datetime($expires_at),
                        hit_count: 0
                    })

                    // 관련 종목과 연결
                    WITH c
                    UNWIND $entities as symbol
                    MERGE (s:Stock {symbol: symbol})
                    MERGE (c)-[:ANALYZED]->(s)
                """, {
                    'cache_id': cache_id,
                    'question': question,
                    'embedding': embedding,
                    'response': response,
                    'suggestions': suggestions_json,  # JSON 문자열로 저장
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                    'user_id': user_id,
                    'session_id': session_id,
                    'entities': entities or [],
                    'expires_at': expires_at.isoformat()
                })

                logger.info(f"Cache stored: {cache_id} (expires: {expires_at.date()})")
                return cache_id

        except Exception as e:
            logger.error(f"Failed to store cache: {e}")
            return None

    async def invalidate(
        self,
        cache_id: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> int:
        """
        캐시 무효화

        Args:
            cache_id: 특정 캐시 ID (선택)
            symbol: 특정 종목 관련 캐시 (선택)

        Returns:
            삭제된 캐시 수
        """
        driver = get_neo4j_driver()
        if driver is None:
            return 0

        try:
            with driver.session(database=settings.NEO4J_DATABASE) as session:
                if cache_id:
                    # 특정 캐시 삭제
                    result = session.run("""
                        MATCH (c:AnalysisCache {cache_id: $cache_id})
                        DETACH DELETE c
                        RETURN count(*) as deleted
                    """, {'cache_id': cache_id})

                elif symbol:
                    # 특정 종목 관련 캐시 삭제
                    result = session.run("""
                        MATCH (c:AnalysisCache)-[:ANALYZED]->(s:Stock {symbol: $symbol})
                        DETACH DELETE c
                        RETURN count(*) as deleted
                    """, {'symbol': symbol.upper()})

                else:
                    # 전체 무효화 (주의!)
                    result = session.run("""
                        MATCH (c:AnalysisCache)
                        DETACH DELETE c
                        RETURN count(*) as deleted
                    """)

                record = result.single()
                deleted = record['deleted'] if record else 0

                if deleted > 0:
                    logger.info(f"Invalidated {deleted} cache entries")

                return deleted

        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0

    def get_hit_rate(self, hours: int = 24) -> Dict[str, Any]:
        """
        캐시 히트율 조회

        Args:
            hours: 조회 기간 (시간)

        Returns:
            {
                'total_requests': int,
                'cache_hits': int,
                'hit_rate': float,
                'avg_similarity': float
            }
        """
        driver = get_neo4j_driver()
        if driver is None:
            return {'status': 'unavailable'}

        try:
            with driver.session(database=settings.NEO4J_DATABASE) as session:
                result = session.run("""
                    MATCH (c:AnalysisCache)
                    WHERE c.last_hit_at > datetime() - duration('PT' + $hours + 'H')
                    WITH sum(c.hit_count) as total_hits, count(c) as cache_entries
                    RETURN total_hits, cache_entries
                """, {'hours': str(hours)})

                record = result.single()

                if record:
                    return {
                        'status': 'available',
                        'period_hours': hours,
                        'cache_entries_hit': record['cache_entries'] or 0,
                        'total_hits': record['total_hits'] or 0,
                        'note': 'Hit rate requires request logging integration'
                    }

                return {
                    'status': 'available',
                    'period_hours': hours,
                    'cache_entries_hit': 0,
                    'total_hits': 0
                }

        except Exception as e:
            logger.error(f"Failed to get hit rate: {e}")
            return {'status': 'error', 'error': str(e)}


# 싱글톤 인스턴스
_semantic_cache_instance: Optional[SemanticCacheService] = None


def get_semantic_cache() -> SemanticCacheService:
    """
    SemanticCacheService 싱글톤 반환
    """
    global _semantic_cache_instance
    if _semantic_cache_instance is None:
        _semantic_cache_instance = SemanticCacheService()
    return _semantic_cache_instance
