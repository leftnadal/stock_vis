"""
News Providers Unit Tests

FinnhubNewsProvider, MarketauxNewsProvider 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from news.providers.finnhub import FinnhubNewsProvider
from news.providers.marketaux import MarketauxNewsProvider
from news.providers.base import RawNewsArticle


class TestFinnhubNewsProvider:
    """FinnhubNewsProvider 테스트"""

    @pytest.fixture
    def provider(self):
        """Finnhub Provider 인스턴스 (request_delay=0으로 테스트 속도 향상)"""
        return FinnhubNewsProvider(api_key='test_finnhub_key', request_delay=0)

    def test_init_with_api_key(self):
        """
        Given: API 키 제공
        When: FinnhubNewsProvider 초기화
        Then: 정상 생성
        """
        provider = FinnhubNewsProvider(api_key='test_key')

        assert provider.api_key == 'test_key'
        assert provider.request_delay == 1.0  # 기본값

    def test_init_without_api_key(self):
        """
        Given: API 키 미제공 (빈 문자열)
        When: FinnhubNewsProvider 초기화
        Then: ValueError 발생
        """
        with pytest.raises(ValueError, match="Finnhub API Key not found"):
            FinnhubNewsProvider(api_key='')

    @patch('news.providers.finnhub.requests.get')
    def test_fetch_company_news_success(self, mock_get, provider, sample_finnhub_response):
        """
        Given: 정상적인 Finnhub API 응답
        When: fetch_company_news() 호출
        Then: RawNewsArticle 리스트 반환
        """
        # Mock 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_finnhub_response
        mock_get.return_value = mock_response

        # 테스트 실행
        from_date = datetime(2024, 12, 1)
        to_date = datetime(2024, 12, 8)
        articles = provider.fetch_company_news('AAPL', from_date, to_date)

        # 검증
        assert len(articles) == 2
        assert all(isinstance(a, RawNewsArticle) for a in articles)

        # 첫 번째 기사 검증
        article = articles[0]
        assert article.title == 'Apple Announces Record Q4 Earnings'
        assert article.source == 'Yahoo Finance'
        assert article.provider_name == 'finnhub'
        assert len(article.entities) == 1
        assert article.entities[0]['symbol'] == 'AAPL'

    @patch('news.providers.finnhub.requests.get')
    def test_fetch_company_news_symbol_uppercase(self, mock_get, provider):
        """
        Given: 소문자 심볼 입력
        When: fetch_company_news() 호출
        Then: 대문자로 변환하여 API 요청
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        from_date = datetime(2024, 12, 1)
        to_date = datetime(2024, 12, 8)
        provider.fetch_company_news('aapl', from_date, to_date)

        # API 호출 시 대문자 사용 확인
        call_args = mock_get.call_args
        params = call_args.kwargs.get('params') or call_args.args[1] if len(call_args.args) > 1 else {}
        assert params.get('symbol') == 'AAPL'

    @patch('news.providers.finnhub.requests.get')
    def test_fetch_market_news_success(self, mock_get, provider, sample_finnhub_response):
        """
        Given: 정상적인 Finnhub 시장 뉴스 응답
        When: fetch_market_news() 호출
        Then: RawNewsArticle 리스트 반환
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_finnhub_response
        mock_get.return_value = mock_response

        articles = provider.fetch_market_news(category='general', limit=10)

        assert len(articles) == 2
        assert all(isinstance(a, RawNewsArticle) for a in articles)

    @patch('news.providers.finnhub.requests.get')
    def test_fetch_market_news_limit_applied(self, mock_get, provider):
        """
        Given: Finnhub가 50개 뉴스 반환
        When: fetch_market_news(limit=10) 호출
        Then: 10개만 반환
        """
        # 50개 뉴스 Mock
        many_articles = [
            {
                'id': i,
                'headline': f'News {i}',
                'summary': f'Summary {i}',
                'url': f'https://example.com/news/{i}',
                'source': 'Source',
                'datetime': 1700000000 + i,
                'category': 'general'
            }
            for i in range(50)
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = many_articles
        mock_get.return_value = mock_response

        articles = provider.fetch_market_news(limit=10)

        assert len(articles) == 10

    @patch('news.providers.finnhub.requests.get')
    def test_fetch_news_api_error(self, mock_get, provider):
        """
        Given: Finnhub API 에러 응답
        When: fetch_company_news() 호출
        Then: 빈 리스트 반환 (graceful failure)
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'Invalid API key'}
        mock_get.return_value = mock_response

        articles = provider.fetch_company_news('AAPL', datetime.now(), datetime.now())

        assert articles == []

    @patch('news.providers.finnhub.requests.get')
    def test_fetch_news_http_error(self, mock_get, provider):
        """
        Given: HTTP 500 에러
        When: fetch_company_news() 호출
        Then: requests.HTTPError 발생
        """
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")
        mock_get.return_value = mock_response

        articles = provider.fetch_company_news('AAPL', datetime.now(), datetime.now())

        # graceful failure
        assert articles == []

    def test_parse_article_with_symbol(self, provider, sample_finnhub_single_article):
        """
        Given: Finnhub company news 응답
        When: _parse_article() 호출 (symbol 제공)
        Then: 엔티티에 해당 심볼 포함, match_score=1.0
        """
        article = provider._parse_article(sample_finnhub_single_article, symbol='TSLA')

        assert article.title == 'Tesla Stock Jumps on Delivery Numbers'
        assert article.provider_name == 'finnhub'
        assert article.sentiment_score is None  # Finnhub는 감성 분석 미제공
        assert len(article.entities) == 1
        assert article.entities[0]['symbol'] == 'TSLA'
        assert article.entities[0]['match_score'] == Decimal('1.00000')

    def test_parse_article_with_related_field(self, provider, sample_finnhub_single_article):
        """
        Given: Finnhub market news 응답 (related 필드 있음)
        When: _parse_article() 호출 (symbol 미제공)
        Then: related 필드에서 심볼 추출, match_score=0.8
        """
        article = provider._parse_article(sample_finnhub_single_article, symbol=None)

        assert len(article.entities) == 1
        assert article.entities[0]['symbol'] == 'TSLA'
        assert article.entities[0]['match_score'] == Decimal('0.80000')

    def test_get_rate_limit_info(self, provider):
        """
        Given: FinnhubNewsProvider 인스턴스
        When: get_rate_limit() 호출
        Then: 60 calls per 60 seconds 반환
        """
        rate_limit = provider.get_rate_limit()

        assert rate_limit == {'calls': 60, 'period': 60}

    def test_get_rate_limit_key(self, provider):
        """
        Given: FinnhubNewsProvider 인스턴스
        When: get_rate_limit_key() 호출
        Then: "news_rate_limit:finnhub" 반환
        """
        key = provider.get_rate_limit_key()

        assert key == "news_rate_limit:finnhub"


class TestMarketauxNewsProvider:
    """MarketauxNewsProvider 테스트"""

    @pytest.fixture
    def provider(self):
        """Marketaux Provider 인스턴스 (request_delay=0으로 테스트 속도 향상)"""
        return MarketauxNewsProvider(api_key='test_marketaux_key', request_delay=0)

    def test_init_with_api_key(self):
        """
        Given: API 키 제공
        When: MarketauxNewsProvider 초기화
        Then: 정상 생성
        """
        provider = MarketauxNewsProvider(api_key='test_key')

        assert provider.api_key == 'test_key'
        assert provider.request_delay == 900.0  # 기본값 (15분)

    def test_init_without_api_key(self):
        """
        Given: API 키 미제공
        When: MarketauxNewsProvider 초기화
        Then: ValueError 발생
        """
        with pytest.raises(ValueError, match="Marketaux API Key not found"):
            MarketauxNewsProvider(api_key='')

    @patch('news.providers.marketaux.requests.get')
    def test_fetch_company_news_success(self, mock_get, provider, sample_marketaux_response):
        """
        Given: 정상적인 Marketaux API 응답
        When: fetch_company_news() 호출
        Then: RawNewsArticle 리스트 반환 (엔티티, 감성 분석 포함)
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_marketaux_response
        mock_get.return_value = mock_response

        from_date = datetime(2024, 12, 1)
        to_date = datetime(2024, 12, 8)
        articles = provider.fetch_company_news('AAPL', from_date, to_date)

        assert len(articles) == 2
        assert all(isinstance(a, RawNewsArticle) for a in articles)

        # 첫 번째 기사 검증 (AAPL)
        article = articles[0]
        assert article.title == 'Apple Surpasses Expectations with iPhone Sales'
        assert article.provider_name == 'marketaux'
        assert article.sentiment_score == Decimal('0.75')  # 엔티티 감성 점수
        assert article.sentiment_source == 'marketaux'
        assert len(article.entities) == 1

        entity = article.entities[0]
        assert entity['symbol'] == 'AAPL'
        assert entity['entity_name'] == 'Apple Inc.'
        assert entity['sentiment_score'] == Decimal('0.75')
        assert len(entity['highlights']) == 2

    @patch('news.providers.marketaux.requests.get')
    def test_fetch_market_news_success(self, mock_get, provider, sample_marketaux_response):
        """
        Given: 정상적인 Marketaux 시장 뉴스 응답
        When: fetch_market_news() 호출
        Then: RawNewsArticle 리스트 반환
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_marketaux_response
        mock_get.return_value = mock_response

        articles = provider.fetch_market_news(category='general', limit=3)

        assert len(articles) == 2

    @patch('news.providers.marketaux.requests.get')
    def test_fetch_market_news_limit_capped_at_3(self, mock_get, provider, sample_marketaux_response):
        """
        Given: limit=10 요청
        When: fetch_market_news() 호출
        Then: Free tier 제한으로 limit=3 적용
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_marketaux_response
        mock_get.return_value = mock_response

        provider.fetch_market_news(limit=10)

        call_args = mock_get.call_args
        params = call_args.kwargs.get('params') or call_args.args[1] if len(call_args.args) > 1 else {}
        assert params.get('limit') == 3  # 최대 3개로 제한

    def test_parse_article_with_entities(self, provider, sample_marketaux_single_article):
        """
        Given: Marketaux 응답 (엔티티 포함)
        When: _parse_article() 호출
        Then: 엔티티 정보 파싱됨
        """
        article = provider._parse_article(sample_marketaux_single_article)

        assert article.title == 'Google Announces AI Breakthrough'
        assert article.provider_id == 'single-test-uuid'
        assert len(article.entities) == 1

        entity = article.entities[0]
        assert entity['symbol'] == 'GOOGL'
        assert entity['entity_name'] == 'Alphabet Inc.'
        assert entity['entity_type'] == 'equity'
        assert entity['industry'] == 'Technology'
        assert entity['sentiment_score'] == Decimal('0.85')

    def test_parse_article_with_highlights(self, provider, sample_marketaux_response):
        """
        Given: Marketaux 응답 (하이라이트 포함)
        When: _parse_article() 호출
        Then: 하이라이트 파싱됨
        """
        item = sample_marketaux_response['data'][0]
        article = provider._parse_article(item)

        entity = article.entities[0]
        highlights = entity['highlights']

        assert len(highlights) == 2
        assert highlights[0]['text'] == 'Apple exceeded revenue expectations'
        assert highlights[0]['sentiment'] == Decimal('0.8')
        assert highlights[0]['location'] == 'title'

    def test_safe_decimal_conversion(self, provider):
        """
        Given: 다양한 타입의 값
        When: _safe_decimal() 호출
        Then: 안전하게 Decimal 변환 또는 None 반환
        """
        assert provider._safe_decimal(0.75) == Decimal('0.75')
        assert provider._safe_decimal('0.85') == Decimal('0.85')
        assert provider._safe_decimal(None) is None
        assert provider._safe_decimal('invalid') is None

    def test_get_rate_limit_info(self, provider):
        """
        Given: MarketauxNewsProvider 인스턴스
        When: get_rate_limit() 호출
        Then: 100 calls per day (86400 seconds) 반환
        """
        rate_limit = provider.get_rate_limit()

        assert rate_limit == {'calls': 100, 'period': 86400}

    def test_get_rate_limit_key(self, provider):
        """
        Given: MarketauxNewsProvider 인스턴스
        When: get_rate_limit_key() 호출
        Then: "news_rate_limit:marketaux" 반환
        """
        key = provider.get_rate_limit_key()

        assert key == "news_rate_limit:marketaux"


class TestBaseNewsProvider:
    """BaseNewsProvider 공통 메서드 테스트"""

    @pytest.fixture
    def provider(self):
        """테스트용 Provider 인스턴스"""
        return FinnhubNewsProvider(api_key='test_key')

    def test_normalize_url_basic(self, provider):
        """
        Given: 기본 URL
        When: normalize_url() 호출
        Then: 소문자 변환, 공백 제거
        """
        url = '  https://EXAMPLE.com/News  '
        normalized = provider.normalize_url(url)

        assert normalized == 'https://example.com/news'

    def test_normalize_url_remove_query_params(self, provider):
        """
        Given: 쿼리 파라미터 포함 URL
        When: normalize_url() 호출
        Then: 쿼리 파라미터 제거
        """
        url = 'https://example.com/news?utm_source=twitter&utm_campaign=test'
        normalized = provider.normalize_url(url)

        assert normalized == 'https://example.com/news'
        assert '?' not in normalized

    def test_normalize_url_remove_trailing_slash(self, provider):
        """
        Given: 마지막에 슬래시 있는 URL
        When: normalize_url() 호출
        Then: 마지막 슬래시 제거
        """
        url = 'https://example.com/news/'
        normalized = provider.normalize_url(url)

        assert normalized == 'https://example.com/news'

    def test_normalize_url_idempotent(self, provider):
        """
        Given: 이미 정규화된 URL
        When: normalize_url() 두 번 호출
        Then: 동일한 결과 (idempotent)
        """
        url = 'https://example.com/news'
        normalized1 = provider.normalize_url(url)
        normalized2 = provider.normalize_url(normalized1)

        assert normalized1 == normalized2


# ===== Marker =====

pytestmark = pytest.mark.unit
