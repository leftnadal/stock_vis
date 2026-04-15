"""
BasicCacheService 단위 테스트

Django cache backend를 사용하여 캐시 CRUD 및 키 생성 로직을 검증합니다.
LocMemCache(Django 테스트 기본값)로 실행되므로 Redis 의존성 없음.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from rag_analysis.services.cache import BasicCacheService, get_cache_service


class TestMakeKey:
    """캐시 키 생성 로직"""

    def test_basic_key(self):
        key = BasicCacheService._make_key('graph', 'AAPL')
        assert key == 'rag:graph:AAPL'

    def test_key_uppercases_string_args(self):
        key = BasicCacheService._make_key('graph', 'aapl')
        assert key == 'rag:graph:AAPL'

    def test_key_with_multiple_args(self):
        key = BasicCacheService._make_key('llm', 'default', 'v2')
        assert key == 'rag:llm:DEFAULT:V2'

    def test_key_with_dict_arg_uses_hash(self):
        key = BasicCacheService._make_key('llm', 'default', {'prompt': 'hello'})
        parts = key.split(':')
        assert parts[0] == 'rag'
        assert parts[1] == 'llm'
        assert parts[2] == 'DEFAULT'
        assert len(parts[3]) == 8  # md5 해시 앞 8자

    def test_same_dict_produces_same_key(self):
        d = {'a': 1, 'b': 2}
        key1 = BasicCacheService._make_key('llm', d)
        key2 = BasicCacheService._make_key('llm', d)
        assert key1 == key2

    def test_different_dict_produces_different_key(self):
        key1 = BasicCacheService._make_key('llm', {'prompt': 'hello'})
        key2 = BasicCacheService._make_key('llm', {'prompt': 'world'})
        assert key1 != key2


class TestSerialize:
    """직렬화 / 역직렬화"""

    def test_serialize_dict(self):
        data = {'symbol': 'AAPL', 'price': 150.0}
        result = BasicCacheService._serialize(data)
        assert json.loads(result) == data

    def test_serialize_list(self):
        data = [1, 2, 3]
        result = BasicCacheService._serialize(data)
        assert json.loads(result) == data

    def test_serialize_string(self):
        result = BasicCacheService._serialize('plain text')
        assert result == 'plain text'

    def test_deserialize_json(self):
        raw = json.dumps({'key': 'value'})
        result = BasicCacheService._deserialize(raw)
        assert result == {'key': 'value'}

    def test_deserialize_none(self):
        assert BasicCacheService._deserialize(None) is None

    def test_deserialize_invalid_json(self):
        result = BasicCacheService._deserialize('not json {{')
        assert result == 'not json {{'


class TestGraphContext:
    """그래프 컨텍스트 캐시 CRUD"""

    def setup_method(self):
        self.svc = BasicCacheService()

    @pytest.mark.django_db
    def test_set_and_get_roundtrip(self):
        data = {'symbol': 'AAPL', 'supply_chain': ['TSM', 'QCOM']}
        assert self.svc.set_graph_context('AAPL', data) is True
        result = self.svc.get_graph_context('AAPL')
        assert result == data

    @pytest.mark.django_db
    def test_miss_returns_none(self):
        assert self.svc.get_graph_context('ZZZZ') is None

    @pytest.mark.django_db
    def test_invalidate(self):
        self.svc.set_graph_context('AAPL', {'a': 1})
        assert self.svc.invalidate_graph('AAPL') is True
        assert self.svc.get_graph_context('AAPL') is None

    @pytest.mark.django_db
    def test_get_error_returns_none(self):
        with patch('rag_analysis.services.cache.cache') as mock_cache:
            mock_cache.get.side_effect = ConnectionError('redis down')
            assert self.svc.get_graph_context('AAPL') is None

    @pytest.mark.django_db
    def test_set_error_returns_false(self):
        with patch('rag_analysis.services.cache.cache') as mock_cache:
            mock_cache.set.side_effect = ConnectionError('redis down')
            assert self.svc.set_graph_context('AAPL', {'a': 1}) is False


class TestLLMResponseCache:
    """LLM 응답 캐시"""

    def setup_method(self):
        self.svc = BasicCacheService()

    @pytest.mark.django_db
    def test_set_and_get_roundtrip(self):
        assert self.svc.set_llm_response('hello', 'world') is True
        result = self.svc.get_llm_response('hello')
        assert result == 'world'

    @pytest.mark.django_db
    def test_miss_returns_none(self):
        assert self.svc.get_llm_response('nonexistent') is None

    @pytest.mark.django_db
    def test_custom_model(self):
        self.svc.set_llm_response('q', 'a', model='gemini')
        assert self.svc.get_llm_response('q', model='gemini') == 'a'
        # 다른 모델로는 miss
        assert self.svc.get_llm_response('q', model='claude') is None


class TestAnalysisContextCache:
    """분석 컨텍스트 캐시"""

    def setup_method(self):
        self.svc = BasicCacheService()

    @pytest.mark.django_db
    def test_set_and_get_roundtrip(self):
        ctx = {'symbol': 'MSFT', 'price_data': {'close': 400}}
        assert self.svc.set_analysis_context('MSFT', ctx) is True
        assert self.svc.get_analysis_context('MSFT') == ctx

    @pytest.mark.django_db
    def test_invalidate_analysis_clears_both(self):
        self.svc.set_graph_context('TSLA', {'g': 1})
        self.svc.set_analysis_context('TSLA', {'c': 2})
        assert self.svc.invalidate_analysis('TSLA') is True
        assert self.svc.get_graph_context('TSLA') is None
        assert self.svc.get_analysis_context('TSLA') is None


class TestClearAllAndStats:
    """clear_all, get_stats 유틸리티"""

    def setup_method(self):
        self.svc = BasicCacheService()

    @pytest.mark.django_db
    def test_clear_all_no_pattern_support(self):
        # LocMemCache는 delete_pattern 미지원 → False 반환
        assert self.svc.clear_all() is False

    def test_get_stats_placeholder(self):
        stats = self.svc.get_stats()
        assert stats['graph_keys'] is None
        assert '_note' in stats


class TestSingleton:
    """get_cache_service 싱글톤"""

    def test_returns_same_instance(self):
        import rag_analysis.services.cache as mod
        mod._cache_service = None  # 초기화
        svc1 = get_cache_service()
        svc2 = get_cache_service()
        assert svc1 is svc2
        mod._cache_service = None  # 정리
