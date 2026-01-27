"""
Market Movers 키워드 데이터 수집기 유닛 테스트

pytest 실행:
    pytest tests/serverless/test_keyword_data_collector.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import msgpack

from serverless.services.keyword_data_collector import KeywordDataCollector


class TestKeywordDataCollector:
    """키워드 데이터 수집기 테스트"""

    @pytest.fixture
    def collector(self):
        """수집기 인스턴스"""
        return KeywordDataCollector()

    @pytest.fixture
    def mock_overview_data(self):
        """Alpha Vantage Overview 모의 데이터"""
        return {
            'Symbol': 'AAPL',
            'Name': 'Apple Inc.',
            'Sector': 'Technology',
            'Industry': 'Consumer Electronics',
            'Description': 'Apple Inc. designs, manufactures, and markets smartphones...',
            'MarketCapitalization': '2500000000000',  # 2.5T
            'PERatio': '28.5',
            '52WeekHigh': '199.62',
            '52WeekLow': '164.08',
            'DividendYield': '0.0045',  # 0.45%
        }

    @pytest.fixture
    def expected_context(self):
        """예상 컨텍스트"""
        return {
            'overview': {
                'description': 'Apple Inc. designs, manufactures, and markets smartphones...',
                'market_cap': '2.50T',
                'pe_ratio': 28.5,
                '52_week_high': 199.62,
                '52_week_low': 164.08,
                'dividend_yield': 0.45,
            },
            'news': [],
            'indicators': {}
        }

    def test_init(self, collector):
        """초기화 테스트"""
        assert collector.av_client is not None
        assert collector.rate_limiter is not None
        assert collector.MAX_WORKERS == 5
        assert collector.CACHE_TTL == 3600

    def test_fetch_overview(self, collector, mock_overview_data):
        """Overview 수집 테스트"""
        # av_client Mock 설정 (인스턴스 속성 직접 교체)
        collector.av_client = MagicMock()
        collector.av_client.get_company_overview.return_value = mock_overview_data
        collector.rate_limiter = MagicMock()

        result = collector._fetch_overview('AAPL')

        assert result is not None
        assert 'description' in result
        assert result['market_cap'] == '2.50T'
        assert result['pe_ratio'] == 28.5
        assert result['52_week_high'] == 199.62
        assert result['52_week_low'] == 164.08

    @patch('serverless.services.keyword_data_collector.cache')
    def test_get_cached_context_hit(self, mock_cache, collector):
        """캐시 HIT 테스트"""
        # 모의 캐시 데이터 (msgpack 압축)
        cached_data = {
            'overview': {'market_cap': '2.50T'},
            'news': [],
            'indicators': {}
        }
        compressed = msgpack.packb(cached_data, use_bin_type=True)
        mock_cache.get.return_value = compressed

        result = collector.get_cached_context('2026-01-07', 'AAPL')

        assert result == cached_data
        mock_cache.get.assert_called_once_with('keyword_context:2026-01-07:AAPL')

    @patch('serverless.services.keyword_data_collector.cache')
    def test_get_cached_context_miss(self, mock_cache, collector):
        """캐시 MISS 테스트"""
        mock_cache.get.return_value = None

        result = collector.get_cached_context('2026-01-07', 'AAPL')

        assert result is None

    @patch('serverless.services.keyword_data_collector.cache')
    def test_set_cached_context(self, mock_cache, collector):
        """캐시 저장 테스트"""
        data = {
            'overview': {'market_cap': '2.50T'},
            'news': [],
            'indicators': {}
        }

        result = collector.set_cached_context('2026-01-07', 'AAPL', data)

        assert result is True
        mock_cache.set.assert_called_once()

        # 압축 확인
        call_args = mock_cache.set.call_args
        cache_key = call_args[0][0]
        compressed = call_args[0][1]
        timeout = call_args[1]['timeout']

        assert cache_key == 'keyword_context:2026-01-07:AAPL'
        assert timeout == 3600

        # 압축 해제 확인
        decompressed = msgpack.unpackb(compressed, raw=False)
        assert decompressed == data

    @patch('serverless.services.keyword_data_collector.cache')
    def test_delete_cached_context(self, mock_cache, collector):
        """캐시 삭제 테스트"""
        result = collector.delete_cached_context('2026-01-07', 'AAPL')

        assert result is True
        mock_cache.delete.assert_called_once_with('keyword_context:2026-01-07:AAPL')

    def test_get_batch_contexts(self, collector):
        """배치 컨텍스트 조회 테스트"""
        with patch.object(collector, 'get_cached_context') as mock_get:
            # 모의 데이터
            mock_get.side_effect = [
                {'overview': {}, 'news': [], 'indicators': {}},  # AAPL
                {'overview': {}, 'news': [], 'indicators': {}},  # MSFT
                None,  # GOOGL (캐시 없음)
            ]

            symbols = ['AAPL', 'MSFT', 'GOOGL']
            contexts = collector.get_batch_contexts('2026-01-07', symbols)

            assert len(contexts) == 2  # GOOGL 제외
            assert mock_get.call_count == 3

    def test_estimate_tokens(self, collector):
        """토큰 추정 테스트"""
        contexts = [
            {
                'overview': {'market_cap': '2.50T'},
                'news': [],
                'indicators': {}
            }
        ] * 20  # 20개 종목

        tokens = collector.estimate_tokens(contexts, include_prompt=True)

        assert 'context_tokens' in tokens
        assert 'prompt_tokens' in tokens
        assert 'total_input_tokens' in tokens
        assert 'estimated_output_tokens' in tokens

        # 프롬프트 토큰
        assert tokens['prompt_tokens'] == 1200

        # 출력 토큰: 종목당 300 토큰
        assert tokens['estimated_output_tokens'] == 20 * 300

    def test_empty_context(self, collector):
        """빈 컨텍스트 테스트"""
        context = collector._empty_context()

        assert 'overview' in context
        assert 'news' in context
        assert 'indicators' in context
        assert context['overview'] == {}
        assert context['news'] == []
        assert context['indicators'] == {}

    @patch('serverless.services.keyword_data_collector.AlphaVantageClient')
    @patch('serverless.services.keyword_data_collector.cache')
    def test_collect_single_cache_hit(self, mock_cache, mock_av_client, collector):
        """단일 종목 수집 - 캐시 HIT 테스트"""
        # 캐시 HIT
        cached_data = {'overview': {}, 'news': [], 'indicators': {}}
        compressed = msgpack.packb(cached_data, use_bin_type=True)
        mock_cache.get.return_value = compressed

        result = collector._collect_single('AAPL', date(2026, 1, 7))

        assert result['success'] is True
        assert result['from_cache'] is True
        assert result['error'] is None
        assert result['context'] == cached_data

        # API 호출 없음
        mock_av_client.return_value.get_company_overview.assert_not_called()

    def test_collect_batch(self, collector):
        """배치 수집 테스트 - _collect_single 모킹"""
        # 모의 수집 결과
        mock_results = [
            {
                'success': True,
                'from_cache': False,
                'duration_ms': 1000,
                'error': None,
                'context': {'overview': {}, 'news': [], 'indicators': {}}
            },
            {
                'success': True,
                'from_cache': True,
                'duration_ms': 100,
                'error': None,
                'context': {'overview': {}, 'news': [], 'indicators': {}}
            },
            {
                'success': False,
                'from_cache': False,
                'duration_ms': 500,
                'error': 'HTTPError 429',
                'context': None
            },
        ]

        symbols = ['AAPL', 'MSFT', 'GOOGL']
        target_date = date(2026, 1, 7)

        # _collect_single을 모킹하여 순차적으로 결과 반환
        with patch.object(collector, '_collect_single', side_effect=mock_results):
            result = collector.collect_batch(symbols, target_date)

        assert result['total_stocks'] == 3
        assert len(result['successful']) == 2  # AAPL, MSFT
        assert len(result['failed']) == 1  # GOOGL
        assert result['cache_hits'] == 1  # MSFT
        assert result['api_calls'] == 1  # AAPL
        assert result['duration_ms'] >= 0


@pytest.mark.integration
class TestKeywordDataCollectorIntegration:
    """통합 테스트 (실제 API 호출)"""

    @pytest.mark.skip(reason="Requires Alpha Vantage API key")
    def test_collect_single_real_api(self):
        """실제 API 호출 테스트 (수동 실행)"""
        collector = KeywordDataCollector()
        result = collector._collect_single('AAPL', date.today())

        assert result['success'] is True
        assert result['context'] is not None
        assert 'overview' in result['context']

    @pytest.mark.skip(reason="Requires Alpha Vantage API key")
    def test_collect_batch_real_api(self):
        """배치 수집 실제 API 호출 테스트 (수동 실행)"""
        collector = KeywordDataCollector()
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        result = collector.collect_batch(symbols, date.today())

        assert result['total_stocks'] == 3
        assert len(result['successful']) >= 2
        assert result['duration_ms'] > 0
