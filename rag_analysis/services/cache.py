"""
Basic Cache Service for RAG Analysis

Redis 기반 캐싱:
    - 그래프 쿼리 결과
    - LLM 응답
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


class BasicCacheService:
    """
    Redis 캐시 서비스 (RAG Analysis용)

    Cache Keys:
        - rag:graph:{symbol} - 그래프 쿼리 결과
        - rag:llm:{hash} - LLM 응답 결과
        - rag:context:{symbol} - 분석 컨텍스트
    """

    # TTL 설정 (초)
    TTL_GRAPH_QUERY = 3600  # 1시간 - 그래프 관계는 자주 변경되지 않음
    TTL_LLM_RESPONSE = 21600  # 6시간 - LLM 응답은 비용이 높으므로 길게 캐싱
    TTL_CONTEXT = 1800  # 30분 - 분석 컨텍스트

    PREFIX = 'rag'

    @staticmethod
    def _make_key(prefix: str, *args) -> str:
        """
        캐시 키 생성

        Args:
            prefix: 키 접두사 (e.g., 'graph', 'llm', 'context')
            *args: 키 구성 요소

        Returns:
            'rag:{prefix}:{arg1}:{arg2}:...'
        """
        parts = [BasicCacheService.PREFIX, prefix]
        for arg in args:
            if isinstance(arg, dict):
                # dict는 JSON으로 변환 후 해시
                arg_str = json.dumps(arg, sort_keys=True)
                arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:8]
                parts.append(arg_hash)
            else:
                parts.append(str(arg).upper())
        return ':'.join(parts)

    @staticmethod
    def _serialize(data: Any) -> str:
        """
        데이터 직렬화

        Note:
            - Django cache backend가 자동으로 pickle 처리
            - 명시적 JSON 직렬화는 디버깅 편의성을 위함
        """
        if isinstance(data, (dict, list)):
            return json.dumps(data, ensure_ascii=False)
        return str(data)

    @staticmethod
    def _deserialize(data: Optional[str]) -> Optional[Any]:
        """
        데이터 역직렬화
        """
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    # ============================================================
    # Graph Query Cache
    # ============================================================

    def get_graph_context(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        그래프 컨텍스트 조회

        Args:
            symbol: 종목 심볼

        Returns:
            {
                'symbol': 'AAPL',
                'supply_chain': [...],
                'competitors': [...],
                'sector_peers': [...],
                '_meta': {...}
            }
        """
        key = self._make_key('graph', symbol)
        try:
            data = cache.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                return self._deserialize(data)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    def set_graph_context(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        그래프 컨텍스트 저장

        Args:
            symbol: 종목 심볼
            data: 그래프 쿼리 결과

        Returns:
            성공 여부
        """
        key = self._make_key('graph', symbol)
        try:
            cache.set(key, self._serialize(data), self.TTL_GRAPH_QUERY)
            logger.debug(f"Cache SET: {key} (TTL={self.TTL_GRAPH_QUERY}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    def invalidate_graph(self, symbol: str) -> bool:
        """
        그래프 캐시 무효화

        Args:
            symbol: 종목 심볼

        Returns:
            성공 여부

        Note:
            - Stock 모델 업데이트 시 호출
        """
        key = self._make_key('graph', symbol)
        try:
            cache.delete(key)
            logger.info(f"Cache INVALIDATE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    # ============================================================
    # LLM Response Cache
    # ============================================================

    def get_llm_response(self, prompt: str, model: str = 'default') -> Optional[str]:
        """
        LLM 응답 조회

        Args:
            prompt: 프롬프트
            model: 모델 이름

        Returns:
            캐시된 LLM 응답 또는 None
        """
        key = self._make_key('llm', model, {'prompt': prompt})
        try:
            data = cache.get(key)
            if data:
                logger.debug(f"LLM Cache HIT: {key}")
                return data
            logger.debug(f"LLM Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"LLM cache get error: {e}")
            return None

    def set_llm_response(
        self,
        prompt: str,
        response: str,
        model: str = 'default',
        ttl: Optional[int] = None
    ) -> bool:
        """
        LLM 응답 저장

        Args:
            prompt: 프롬프트
            response: LLM 응답
            model: 모델 이름
            ttl: 커스텀 TTL (None이면 기본값 사용)

        Returns:
            성공 여부
        """
        key = self._make_key('llm', model, {'prompt': prompt})
        ttl = ttl or self.TTL_LLM_RESPONSE
        try:
            cache.set(key, response, ttl)
            logger.debug(f"LLM Cache SET: {key} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"LLM cache set error: {e}")
            return False

    # ============================================================
    # Analysis Context Cache
    # ============================================================

    def get_analysis_context(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        분석 컨텍스트 조회

        Args:
            symbol: 종목 심볼

        Returns:
            {
                'symbol': 'AAPL',
                'price_data': {...},
                'financial_data': {...},
                'graph_context': {...},
                'indicators': {...}
            }
        """
        key = self._make_key('context', symbol)
        try:
            data = cache.get(key)
            if data:
                logger.debug(f"Context Cache HIT: {key}")
                return self._deserialize(data)
            logger.debug(f"Context Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Context cache get error: {e}")
            return None

    def set_analysis_context(
        self,
        symbol: str,
        context: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        분석 컨텍스트 저장

        Args:
            symbol: 종목 심볼
            context: 분석 컨텍스트
            ttl: 커스텀 TTL (None이면 기본값 사용)

        Returns:
            성공 여부
        """
        key = self._make_key('context', symbol)
        ttl = ttl or self.TTL_CONTEXT
        try:
            cache.set(key, self._serialize(context), ttl)
            logger.debug(f"Context Cache SET: {key} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Context cache set error: {e}")
            return False

    def invalidate_analysis(self, symbol: str) -> bool:
        """
        분석 관련 모든 캐시 무효화

        Args:
            symbol: 종목 심볼

        Returns:
            성공 여부

        Note:
            - 주가 업데이트 시 호출
            - graph, context 캐시 모두 삭제
        """
        keys = [
            self._make_key('graph', symbol),
            self._make_key('context', symbol)
        ]

        success = True
        for key in keys:
            try:
                cache.delete(key)
                logger.debug(f"Cache INVALIDATE: {key}")
            except Exception as e:
                logger.error(f"Cache delete error for {key}: {e}")
                success = False

        return success

    # ============================================================
    # Utility Methods
    # ============================================================

    def clear_all(self) -> bool:
        """
        RAG 관련 모든 캐시 삭제

        Warning:
            - 개발/테스트 용도로만 사용
            - Production에서는 주의해서 사용
        """
        try:
            # Django cache backend에 따라 다르게 처리
            # Redis backend인 경우 패턴 매칭 가능
            cache.delete_pattern(f"{self.PREFIX}:*")
            logger.warning("All RAG caches cleared")
            return True
        except AttributeError:
            # delete_pattern 미지원 backend
            logger.warning("Cache backend does not support pattern deletion")
            return False
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회 (Redis backend만 지원)

        Returns:
            {
                'graph_keys': int,
                'llm_keys': int,
                'context_keys': int,
                'total_memory': str
            }
        """
        # 구현은 Redis backend 의존적이므로 선택사항
        # 현재는 placeholder만 제공
        return {
            'graph_keys': None,
            'llm_keys': None,
            'context_keys': None,
            'total_memory': 'N/A',
            '_note': 'Stats require Redis backend with pattern scan support'
        }


# Singleton instance
_cache_service: Optional[BasicCacheService] = None


def get_cache_service() -> BasicCacheService:
    """
    Cache Service singleton 반환
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = BasicCacheService()
    return _cache_service
