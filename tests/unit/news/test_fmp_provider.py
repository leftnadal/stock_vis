"""
FMP News Provider 테스트

FMPNewsProvider의 뉴스 파싱, 날짜 필터링, 에러 처리를 검증합니다.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from news.providers.fmp import FMPNewsProvider
from news.providers.base import RawNewsArticle


# ===== Fixtures =====

@pytest.fixture
def mock_fmp_client():
    """Mock FMPClient"""
    return Mock()


@pytest.fixture
def provider(mock_fmp_client):
    """FMPNewsProvider 인스턴스"""
    return FMPNewsProvider(fmp_client=mock_fmp_client)


@pytest.fixture
def sample_stock_news():
    """FMP stock-news API 응답 샘플"""
    return [
        {
            'symbol': 'AAPL',
            'publishedDate': '2024-12-08 10:30:00',
            'title': 'Apple Announces Record Q4 Earnings',
            'image': 'https://example.com/apple.jpg',
            'site': 'Bloomberg',
            'text': 'Apple Inc. reported record quarterly revenue of $120 billion...',
            'url': 'https://bloomberg.com/apple-q4-earnings',
            'sentiment': 0.75,
        },
        {
            'symbol': 'AAPL',
            'publishedDate': '2024-12-07 14:00:00',
            'title': 'iPhone Sales Surge in Holiday Season',
            'image': 'https://example.com/iphone.jpg',
            'site': 'CNBC',
            'text': 'iPhone sales exceeded expectations...',
            'url': 'https://cnbc.com/iphone-sales',
            'sentiment': 0.5,
        },
    ]


@pytest.fixture
def sample_general_news():
    """FMP general-news API 응답 샘플"""
    return [
        {
            'publishedDate': '2024-12-08 09:00:00',
            'title': 'Fed Signals Rate Cut in 2025',
            'image': 'https://example.com/fed.jpg',
            'site': 'Reuters',
            'text': 'Federal Reserve officials signaled...',
            'url': 'https://reuters.com/fed-rate-cut',
        },
    ]


@pytest.fixture
def sample_press_releases():
    """FMP press-releases API 응답 샘플"""
    return [
        {
            'symbol': 'AAPL',
            'date': '2024-12-08 16:00:00',
            'title': 'Apple Inc. Reports Q4 2024 Results',
            'text': 'CUPERTINO, California — Apple today announced...',
            'url': 'https://apple.com/press/q4-2024',
        },
    ]


# ===== Tests: fetch_company_news =====

class TestFMPNewsProvider:
    """FMPNewsProvider 테스트"""

    def test_init(self, provider, mock_fmp_client):
        """Given FMPClient, When init, Then client 참조 설정"""
        assert provider.client is mock_fmp_client

    def test_fetch_company_news_success(self, provider, mock_fmp_client, sample_stock_news):
        """Given valid response, When fetch, Then RawNewsArticle 리스트 반환"""
        mock_fmp_client.get_stock_news.return_value = sample_stock_news

        from_date = datetime(2024, 12, 1)
        to_date = datetime(2024, 12, 31)
        articles = provider.fetch_company_news('aapl', from_date, to_date)

        assert len(articles) == 2
        assert all(isinstance(a, RawNewsArticle) for a in articles)
        mock_fmp_client.get_stock_news.assert_called_once_with('AAPL', limit=50)

    def test_fetch_company_news_symbol_upper(self, provider, mock_fmp_client, sample_stock_news):
        """Given lowercase symbol, When fetch, Then uppercase로 API 호출"""
        mock_fmp_client.get_stock_news.return_value = sample_stock_news

        provider.fetch_company_news('aapl', datetime(2024, 12, 1), datetime(2024, 12, 31))
        mock_fmp_client.get_stock_news.assert_called_once_with('AAPL', limit=50)

    def test_fetch_company_news_date_filter(self, provider, mock_fmp_client, sample_stock_news):
        """Given date range, When fetch, Then 범위 내 기사만 반환"""
        mock_fmp_client.get_stock_news.return_value = sample_stock_news

        # 12/8만 포함하는 범위
        articles = provider.fetch_company_news(
            'AAPL',
            datetime(2024, 12, 8, 0, 0, 0),
            datetime(2024, 12, 8, 23, 59, 59),
        )

        assert len(articles) == 1
        assert articles[0].title == 'Apple Announces Record Q4 Earnings'

    def test_fetch_company_news_empty_response(self, provider, mock_fmp_client):
        """Given empty response, When fetch, Then 빈 리스트 반환"""
        mock_fmp_client.get_stock_news.return_value = []
        articles = provider.fetch_company_news('AAPL', datetime(2024, 12, 1), datetime(2024, 12, 31))
        assert articles == []

    def test_fetch_company_news_api_error(self, provider, mock_fmp_client):
        """Given API error, When fetch, Then 빈 리스트 반환 (graceful)"""
        mock_fmp_client.get_stock_news.side_effect = Exception("API Error")
        articles = provider.fetch_company_news('AAPL', datetime(2024, 12, 1), datetime(2024, 12, 31))
        assert articles == []

    def test_parse_article_fields(self, provider, sample_stock_news):
        """Given raw data, When parse, Then 필드 정확히 매핑"""
        article = provider._parse_article(sample_stock_news[0], symbol='AAPL')

        assert article is not None
        assert article.url == 'https://bloomberg.com/apple-q4-earnings'
        assert article.title == 'Apple Announces Record Q4 Earnings'
        assert article.source == 'Bloomberg'
        assert article.provider_name == 'fmp'
        assert article.category == 'company'
        assert article.sentiment_score == Decimal('0.75')
        assert article.sentiment_source == 'fmp'
        assert len(article.entities) == 1
        assert article.entities[0]['symbol'] == 'AAPL'
        assert article.entities[0]['source'] == 'fmp'

    def test_parse_article_no_url(self, provider):
        """Given item without url, When parse, Then None"""
        result = provider._parse_article({'title': 'Test', 'publishedDate': '2024-12-08'})
        assert result is None

    def test_parse_article_no_title(self, provider):
        """Given item without title, When parse, Then None"""
        result = provider._parse_article({'url': 'https://test.com', 'publishedDate': '2024-12-08'})
        assert result is None

    def test_parse_article_no_sentiment(self, provider):
        """Given item without sentiment, When parse, Then sentiment_source='none'"""
        item = {
            'url': 'https://test.com/news',
            'title': 'Test News',
            'publishedDate': '2024-12-08 10:00:00',
            'site': 'Test',
            'text': 'Summary',
        }
        article = provider._parse_article(item)
        assert article.sentiment_score is None
        assert article.sentiment_source == 'none'

    # ===== Tests: fetch_market_news =====

    def test_fetch_market_news_success(self, provider, mock_fmp_client, sample_general_news):
        """Given valid response, When fetch_market_news, Then articles 반환"""
        mock_fmp_client.get_general_news.return_value = sample_general_news
        articles = provider.fetch_market_news(limit=50)
        assert len(articles) == 1
        assert articles[0].category == 'general'
        assert articles[0].source == 'Reuters'

    def test_fetch_market_news_api_error(self, provider, mock_fmp_client):
        """Given API error, When fetch_market_news, Then 빈 리스트"""
        mock_fmp_client.get_general_news.side_effect = Exception("Network Error")
        articles = provider.fetch_market_news()
        assert articles == []

    # ===== Tests: fetch_press_releases =====

    def test_fetch_press_releases_success(self, provider, mock_fmp_client, sample_press_releases):
        """Given valid response, When fetch_press_releases, Then articles 반환"""
        mock_fmp_client.get_press_releases.return_value = sample_press_releases
        articles = provider.fetch_press_releases('AAPL')
        assert len(articles) == 1
        assert articles[0].is_press_release is True
        assert articles[0].category == 'press_release'

    def test_fetch_press_releases_entity(self, provider, mock_fmp_client, sample_press_releases):
        """Given press release, When parse, Then symbol entity 포함"""
        mock_fmp_client.get_press_releases.return_value = sample_press_releases
        articles = provider.fetch_press_releases('aapl')
        assert articles[0].entities[0]['symbol'] == 'AAPL'

    # ===== Tests: date parsing =====

    def test_parse_date_datetime_format(self, provider):
        """Given 'YYYY-MM-DD HH:MM:SS', When parse, Then datetime"""
        result = FMPNewsProvider._parse_date('2024-12-08 10:30:00')
        assert result == datetime(2024, 12, 8, 10, 30, 0)

    def test_parse_date_iso_format(self, provider):
        """Given 'YYYY-MM-DDTHH:MM:SS', When parse, Then datetime"""
        result = FMPNewsProvider._parse_date('2024-12-08T10:30:00')
        assert result == datetime(2024, 12, 8, 10, 30, 0)

    def test_parse_date_date_only(self, provider):
        """Given 'YYYY-MM-DD', When parse, Then datetime (midnight)"""
        result = FMPNewsProvider._parse_date('2024-12-08')
        assert result == datetime(2024, 12, 8, 0, 0, 0)

    def test_parse_date_invalid(self, provider):
        """Given invalid string, When parse, Then None"""
        result = FMPNewsProvider._parse_date('not-a-date')
        assert result is None

    def test_parse_date_empty(self, provider):
        """Given empty string, When parse, Then None"""
        result = FMPNewsProvider._parse_date('')
        assert result is None

    # ===== Tests: safe_decimal =====

    def test_safe_decimal_float(self, provider):
        """Given float, When safe_decimal, Then Decimal"""
        assert FMPNewsProvider._safe_decimal(0.75) == Decimal('0.75')

    def test_safe_decimal_clamp(self, provider):
        """Given out-of-range, When safe_decimal, Then clamped"""
        assert FMPNewsProvider._safe_decimal(2.0) == Decimal('1.000')
        assert FMPNewsProvider._safe_decimal(-2.0) == Decimal('-1.000')

    def test_safe_decimal_none(self, provider):
        """Given None, When safe_decimal, Then None"""
        assert FMPNewsProvider._safe_decimal(None) is None

    def test_safe_decimal_invalid(self, provider):
        """Given invalid string, When safe_decimal, Then None"""
        assert FMPNewsProvider._safe_decimal('not-a-number') is None

    # ===== Tests: rate limit info =====

    def test_rate_limit_key(self, provider):
        assert provider.get_rate_limit_key() == "news_rate_limit:fmp"

    def test_rate_limit(self, provider):
        assert provider.get_rate_limit() == {'calls': 300, 'period': 60}

    # ===== Tests: summary truncation =====

    def test_long_summary_truncated(self, provider):
        """Given very long text, When parse, Then summary truncated to 2000 chars"""
        item = {
            'url': 'https://test.com/long',
            'title': 'Long Article',
            'publishedDate': '2024-12-08 10:00:00',
            'site': 'Test',
            'text': 'A' * 5000,
        }
        article = provider._parse_article(item)
        assert len(article.summary) == 2000


pytestmark = pytest.mark.unit
