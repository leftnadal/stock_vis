"""
Alpha Vantage News Provider 테스트

AlphaVantageNewsProvider의 뉴스 파싱, 감성 점수, rate limiting을 검증합니다.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from news.providers.alphavantage import AlphaVantageNewsProvider, RateLimitExceeded
from news.providers.base import RawNewsArticle


# ===== Fixtures =====

@pytest.fixture
def provider():
    """AlphaVantageNewsProvider 인스턴스"""
    return AlphaVantageNewsProvider(api_key='test_av_key')


@pytest.fixture
def sample_av_response():
    """Alpha Vantage NEWS_SENTIMENT API 응답 샘플"""
    return {
        'items': '1',
        'sentiment_score_definition': '...',
        'relevance_score_definition': '...',
        'feed': [
            {
                'title': 'Apple Beats Earnings Expectations',
                'url': 'https://finance.yahoo.com/apple-earnings',
                'time_published': '20241208T103000',
                'authors': ['John Doe'],
                'summary': 'Apple reported stronger-than-expected Q4 earnings...',
                'banner_image': 'https://example.com/apple-banner.jpg',
                'source': 'Yahoo Finance',
                'category_within_source': 'Technology',
                'source_domain': 'finance.yahoo.com',
                'topics': [
                    {'topic': 'Earnings', 'relevance_score': '0.99'},
                ],
                'overall_sentiment_score': 0.75,
                'overall_sentiment_label': 'Bullish',
                'ticker_sentiment': [
                    {
                        'ticker': 'AAPL',
                        'relevance_score': '0.95',
                        'ticker_sentiment_score': '0.8',
                        'ticker_sentiment_label': 'Bullish',
                    },
                    {
                        'ticker': 'MSFT',
                        'relevance_score': '0.3',
                        'ticker_sentiment_score': '0.2',
                        'ticker_sentiment_label': 'Somewhat-Bullish',
                    },
                ],
            },
        ],
    }


@pytest.fixture
def sample_av_no_sentiment():
    """감성 점수 없는 AV 응답"""
    return {
        'feed': [
            {
                'title': 'Market Update',
                'url': 'https://example.com/market-update',
                'time_published': '20241208T090000',
                'summary': 'Markets opened mixed today...',
                'source': 'Reuters',
                'ticker_sentiment': [],
            },
        ],
    }


# ===== Tests =====

class TestAlphaVantageNewsProvider:
    """AlphaVantageNewsProvider 테스트"""

    def test_init(self, provider):
        """Given api_key, When init, Then key 설정"""
        assert provider.api_key == 'test_av_key'

    @patch('news.providers.alphavantage.requests.get')
    @patch('news.providers.alphavantage.AlphaVantageNewsProvider._acquire_token')
    def test_fetch_company_news_success(
        self, mock_token, mock_get, provider, sample_av_response
    ):
        """Given valid response, When fetch, Then RawNewsArticle 리스트 반환"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_av_response
        mock_get.return_value = mock_response

        from_date = datetime(2024, 12, 1)
        to_date = datetime(2024, 12, 31)
        articles = provider.fetch_company_news('AAPL', from_date, to_date)

        assert len(articles) == 1
        assert isinstance(articles[0], RawNewsArticle)
        mock_token.assert_called_once()

    @patch('news.providers.alphavantage.requests.get')
    @patch('news.providers.alphavantage.AlphaVantageNewsProvider._acquire_token')
    def test_fetch_company_news_article_fields(
        self, mock_token, mock_get, provider, sample_av_response
    ):
        """Given AV response, When parse, Then 필드 정확히 매핑"""
        mock_response = Mock()
        mock_response.json.return_value = sample_av_response
        mock_get.return_value = mock_response

        articles = provider.fetch_company_news(
            'AAPL', datetime(2024, 12, 1), datetime(2024, 12, 31)
        )
        article = articles[0]

        assert article.title == 'Apple Beats Earnings Expectations'
        assert article.url == 'https://finance.yahoo.com/apple-earnings'
        assert article.source == 'Yahoo Finance'
        assert article.provider_name == 'alpha_vantage'
        assert article.sentiment_score == Decimal('0.75')
        assert article.sentiment_source == 'alpha_vantage'
        assert article.published_at == datetime(2024, 12, 8, 10, 30, 0)

    @patch('news.providers.alphavantage.requests.get')
    @patch('news.providers.alphavantage.AlphaVantageNewsProvider._acquire_token')
    def test_fetch_company_news_entities(
        self, mock_token, mock_get, provider, sample_av_response
    ):
        """Given ticker_sentiment, When parse, Then entities 매핑"""
        mock_response = Mock()
        mock_response.json.return_value = sample_av_response
        mock_get.return_value = mock_response

        articles = provider.fetch_company_news(
            'AAPL', datetime(2024, 12, 1), datetime(2024, 12, 31)
        )
        entities = articles[0].entities

        # AAPL과 MSFT 두 개의 entity
        symbols = [e['symbol'] for e in entities]
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols

        aapl_entity = next(e for e in entities if e['symbol'] == 'AAPL')
        assert aapl_entity['source'] == 'alpha_vantage'
        assert aapl_entity['sentiment_score'] == Decimal('0.8')

    @patch('news.providers.alphavantage.requests.get')
    @patch('news.providers.alphavantage.AlphaVantageNewsProvider._acquire_token')
    def test_fetch_company_news_adds_missing_symbol(
        self, mock_token, mock_get, provider, sample_av_no_sentiment
    ):
        """Given empty ticker_sentiment, When fetch, Then 요청 심볼이 entity에 추가됨"""
        mock_response = Mock()
        mock_response.json.return_value = sample_av_no_sentiment
        mock_get.return_value = mock_response

        articles = provider.fetch_company_news(
            'GOOG', datetime(2024, 12, 1), datetime(2024, 12, 31)
        )
        entities = articles[0].entities

        assert len(entities) == 1
        assert entities[0]['symbol'] == 'GOOG'
        assert entities[0]['source'] == 'alpha_vantage'

    @patch('news.providers.alphavantage.requests.get')
    @patch('news.providers.alphavantage.AlphaVantageNewsProvider._acquire_token')
    def test_fetch_company_news_rate_limit_response(
        self, mock_token, mock_get, provider
    ):
        """Given AV rate limit Note, When fetch, Then RateLimitExceeded"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'Note': 'Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute...'
        }
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitExceeded):
            provider.fetch_company_news(
                'AAPL', datetime(2024, 12, 1), datetime(2024, 12, 31)
            )

    @patch('news.providers.alphavantage.requests.get')
    @patch('news.providers.alphavantage.AlphaVantageNewsProvider._acquire_token')
    def test_fetch_company_news_api_error(
        self, mock_token, mock_get, provider
    ):
        """Given API error, When fetch, Then 빈 리스트"""
        mock_get.side_effect = Exception("Network Error")
        articles = provider.fetch_company_news(
            'AAPL', datetime(2024, 12, 1), datetime(2024, 12, 31)
        )
        assert articles == []

    @patch('news.providers.alphavantage.AlphaVantageNewsProvider._acquire_token')
    def test_fetch_company_news_token_rejected(self, mock_token, provider):
        """Given rate limit exceeded, When acquire_token fails, Then RateLimitExceeded"""
        mock_token.side_effect = RateLimitExceeded("5/min exceeded")

        with pytest.raises(RateLimitExceeded):
            provider.fetch_company_news(
                'AAPL', datetime(2024, 12, 1), datetime(2024, 12, 31)
            )

    # ===== Tests: fetch_market_news =====

    def test_fetch_market_news_returns_empty(self, provider):
        """AV는 market news를 지원하지 않음 → 빈 리스트"""
        articles = provider.fetch_market_news()
        assert articles == []

    # ===== Tests: date parsing =====

    def test_parse_av_date_full(self):
        """Given YYYYMMDDTHHmmss, When parse, Then datetime"""
        result = AlphaVantageNewsProvider._parse_av_date('20241208T103000')
        assert result == datetime(2024, 12, 8, 10, 30, 0)

    def test_parse_av_date_short(self):
        """Given YYYYMMDDTHHmm (4-digit), When parse, Then datetime"""
        result = AlphaVantageNewsProvider._parse_av_date('20241208T1030')
        # strptime '%Y%m%dT%H%M' parses '1030' as H=10, M=30
        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.hour == 10

    def test_parse_av_date_invalid(self):
        """Given invalid string, When parse, Then None"""
        result = AlphaVantageNewsProvider._parse_av_date('not-a-date')
        assert result is None

    def test_parse_av_date_empty(self):
        """Given empty string, When parse, Then None"""
        result = AlphaVantageNewsProvider._parse_av_date('')
        assert result is None

    # ===== Tests: rate limit info =====

    def test_rate_limit_key(self, provider):
        assert provider.get_rate_limit_key() == "news_rate_limit:alpha_vantage"

    def test_rate_limit(self, provider):
        assert provider.get_rate_limit() == {'calls': 5, 'period': 60}

    # ===== Tests: _acquire_token =====

    @patch('django.core.cache.cache')
    def test_acquire_token_success(self, mock_cache, provider):
        """Given under limit, When acquire, Then success"""
        mock_cache.get.return_value = 3  # 3/5 사용
        result = provider._acquire_token()
        assert result is True

    @patch('django.core.cache.cache')
    def test_acquire_token_exceeded(self, mock_cache, provider):
        """Given at limit, When acquire, Then RateLimitExceeded"""
        mock_cache.get.return_value = 5  # 5/5 사용
        with pytest.raises(RateLimitExceeded):
            provider._acquire_token()


pytestmark = pytest.mark.unit
