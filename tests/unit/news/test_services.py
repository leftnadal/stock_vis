"""
News Services Unit Tests

NewsDeduplicator, NewsAggregatorService 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from news.services.deduplicator import NewsDeduplicator
from news.services.aggregator import NewsAggregatorService
from news.providers.base import RawNewsArticle


class TestNewsDeduplicator:
    """NewsDeduplicator 테스트"""

    @pytest.fixture
    def deduplicator(self):
        """NewsDeduplicator 인스턴스"""
        return NewsDeduplicator(title_similarity_threshold=0.85)

    def test_init_with_custom_threshold(self):
        """
        Given: 커스텀 유사도 임계값 제공
        When: NewsDeduplicator 초기화
        Then: 설정된 임계값 저장
        """
        dedup = NewsDeduplicator(title_similarity_threshold=0.9)

        assert dedup.title_similarity_threshold == 0.9

    def test_deduplicate_empty_list(self, deduplicator):
        """
        Given: 빈 리스트
        When: deduplicate() 호출
        Then: 빈 리스트 반환
        """
        result = deduplicator.deduplicate([])

        assert result == []

    def test_deduplicate_by_url(self, deduplicator):
        """
        Given: 동일한 URL(정규화 후)의 뉴스 2개
        When: deduplicate() 호출
        Then: 1개만 반환 (URL 중복 제거)
        """
        now = datetime.now()
        articles = [
            RawNewsArticle(
                url='https://example.com/news/1',
                title='Test News 1',
                summary='Summary',
                source='Source A',
                published_at=now,
                image_url='',
                language='en',
                category='general',
                provider_id='1',
                provider_name='finnhub',
                sentiment_score=None,
                sentiment_source='none',
                entities=[],
                is_press_release=False
            ),
            RawNewsArticle(
                url='https://EXAMPLE.COM/news/1',  # 대소문자 다름
                title='Test News 1 Duplicate',
                summary='Summary',
                source='Source B',
                published_at=now,
                image_url='',
                language='en',
                category='general',
                provider_id='2',
                provider_name='finnhub',
                sentiment_score=None,
                sentiment_source='none',
                entities=[],
                is_press_release=False
            )
        ]

        result = deduplicator.deduplicate(articles)

        assert len(result) == 1
        assert result[0].url == articles[0].url

    def test_deduplicate_by_title_similarity(self, deduplicator):
        """
        Given: URL은 다르지만 제목이 유사한 뉴스 2개
        When: deduplicate() 호출 (유사도 임계값=0.85)
        Then: 1개만 반환 (제목 중복 제거)
        """
        now = datetime.now()
        articles = [
            RawNewsArticle(
                url='https://source-a.com/news/1',
                title='Apple Announces Record Quarterly Earnings',
                summary='Summary 1',
                source='Source A',
                published_at=now,
                image_url='',
                language='en',
                category='company',
                provider_id='1',
                provider_name='finnhub',
                sentiment_score=None,
                sentiment_source='none',
                entities=[],
                is_press_release=False
            ),
            RawNewsArticle(
                url='https://source-b.com/news/2',
                title='Apple Announces Record Quarterly Earnings Results',  # 거의 동일
                summary='Summary 2',
                source='Source B',
                published_at=now,
                image_url='',
                language='en',
                category='company',
                provider_id='2',
                provider_name='marketaux',
                sentiment_score=None,
                sentiment_source='none',
                entities=[],
                is_press_release=False
            )
        ]

        result = deduplicator.deduplicate(articles)

        assert len(result) == 1

    def test_deduplicate_preserves_unique_articles(self, deduplicator, duplicate_news_articles):
        """
        Given: 중복 제거 테스트용 뉴스 리스트 (5개 입력, 2개 중복)
        When: deduplicate() 호출
        Then: 3개 유니크 뉴스만 반환
        """
        result = deduplicator.deduplicate(duplicate_news_articles)

        # 예상: URL 중복 2개 → 1개, 제목 유사 2개 → 1개, 유니크 1개 = 총 3개
        assert len(result) == 3

    def test_calculate_url_hash(self, deduplicator):
        """
        Given: URL 문자열
        When: _calculate_url_hash() 호출
        Then: SHA256 해시 반환
        """
        import hashlib

        url = 'https://example.com/news'
        expected_hash = hashlib.sha256(url.lower().encode()).hexdigest()

        result = deduplicator._calculate_url_hash(url)

        assert result == expected_hash

    def test_calculate_url_hash_case_insensitive(self, deduplicator):
        """
        Given: 대소문자만 다른 URL 2개
        When: _calculate_url_hash() 호출
        Then: 동일한 해시 반환
        """
        url1 = 'https://EXAMPLE.com/News'
        url2 = 'https://example.com/news'

        hash1 = deduplicator._calculate_url_hash(url1)
        hash2 = deduplicator._calculate_url_hash(url2)

        assert hash1 == hash2

    def test_calculate_title_similarity_identical(self, deduplicator):
        """
        Given: 동일한 제목
        When: _calculate_title_similarity() 호출
        Then: 1.0 반환
        """
        title = 'Apple Announces New Product'

        similarity = deduplicator._calculate_title_similarity(title, title)

        assert similarity == 1.0

    def test_calculate_title_similarity_different(self, deduplicator):
        """
        Given: 완전히 다른 제목
        When: _calculate_title_similarity() 호출
        Then: 낮은 유사도 반환
        """
        title1 = 'Apple Announces New iPhone'
        title2 = 'Tesla Stock Jumps on Delivery Numbers'

        similarity = deduplicator._calculate_title_similarity(title1, title2)

        assert similarity < 0.5

    def test_calculate_title_similarity_case_insensitive(self, deduplicator):
        """
        Given: 대소문자만 다른 제목
        When: _calculate_title_similarity() 호출
        Then: 1.0 반환 (대소문자 무시)
        """
        title1 = 'Breaking News Today'
        title2 = 'BREAKING NEWS TODAY'

        similarity = deduplicator._calculate_title_similarity(title1, title2)

        assert similarity == 1.0

    def test_calculate_title_similarity_whitespace_normalized(self, deduplicator):
        """
        Given: 공백 수만 다른 제목
        When: _calculate_title_similarity() 호출
        Then: 1.0 반환 (공백 정규화)
        """
        title1 = 'Apple   Announces    New iPhone'
        title2 = 'Apple Announces New iPhone'

        similarity = deduplicator._calculate_title_similarity(title1, title2)

        assert similarity == 1.0


class TestNewsAggregatorService:
    """NewsAggregatorService 테스트"""

    @pytest.fixture
    def mock_settings(self, monkeypatch):
        """Django settings 모킹"""
        monkeypatch.setattr('news.services.aggregator.settings.FINNHUB_API_KEY', 'test_finnhub')
        monkeypatch.setattr('news.services.aggregator.settings.MARKETAUX_API_KEY', 'test_marketaux')

    @pytest.fixture
    def service(self, mock_settings):
        """NewsAggregatorService 인스턴스"""
        return NewsAggregatorService()

    @pytest.mark.django_db
    @patch('news.services.aggregator.FinnhubNewsProvider.fetch_company_news')
    @patch('news.services.aggregator.MarketauxNewsProvider.fetch_company_news')
    def test_fetch_and_save_company_news_both_providers(
        self,
        mock_marketaux,
        mock_finnhub,
        service,
        raw_news_article_aapl,
        raw_news_article_msft
    ):
        """
        Given: Finnhub + Marketaux 모두 뉴스 반환
        When: fetch_and_save_company_news() 호출 (use_marketaux=True)
        Then: 두 Provider의 뉴스 통합 후 저장
        """
        mock_finnhub.return_value = [raw_news_article_aapl]
        mock_marketaux.return_value = [raw_news_article_msft]

        result = service.fetch_and_save_company_news('AAPL', days=7, use_marketaux=True)

        assert result['symbol'] == 'AAPL'
        assert result['total_fetched'] == 2
        assert result['saved'] >= 1  # 중복 제거 후

    @pytest.mark.django_db
    @patch('news.services.aggregator.FinnhubNewsProvider.fetch_company_news')
    def test_fetch_and_save_company_news_finnhub_only(
        self,
        mock_finnhub,
        service,
        raw_news_article_aapl
    ):
        """
        Given: Finnhub만 사용 (use_marketaux=False)
        When: fetch_and_save_company_news() 호출
        Then: Finnhub 뉴스만 저장
        """
        mock_finnhub.return_value = [raw_news_article_aapl]

        result = service.fetch_and_save_company_news('AAPL', days=7, use_marketaux=False)

        assert result['total_fetched'] == 1
        assert result['saved'] == 1
        mock_finnhub.assert_called_once()

    @pytest.mark.django_db
    @patch('news.services.aggregator.FinnhubNewsProvider.fetch_company_news')
    def test_fetch_and_save_company_news_symbol_uppercase(self, mock_finnhub, service):
        """
        Given: 소문자 심볼 입력
        When: fetch_and_save_company_news() 호출
        Then: 대문자로 변환하여 처리
        """
        mock_finnhub.return_value = []

        result = service.fetch_and_save_company_news('aapl')

        assert result['symbol'] == 'AAPL'

    @pytest.mark.django_db
    @patch('news.services.aggregator.FinnhubNewsProvider.fetch_company_news')
    def test_fetch_and_save_company_news_provider_failure(self, mock_finnhub, service):
        """
        Given: Finnhub API 에러 발생
        When: fetch_and_save_company_news() 호출
        Then: graceful failure (빈 결과 반환)
        """
        mock_finnhub.side_effect = Exception("API error")

        result = service.fetch_and_save_company_news('AAPL')

        assert result['total_fetched'] == 0
        assert result['saved'] == 0

    @pytest.mark.django_db
    @patch('news.services.aggregator.FinnhubNewsProvider.fetch_market_news')
    def test_fetch_and_save_market_news(self, mock_finnhub, service, raw_news_article_aapl):
        """
        Given: Finnhub 시장 뉴스 반환
        When: fetch_and_save_market_news() 호출
        Then: 뉴스 저장 및 결과 반환
        """
        mock_finnhub.return_value = [raw_news_article_aapl]

        result = service.fetch_and_save_market_news(category='general')

        assert result['category'] == 'general'
        assert result['total_fetched'] == 1
        assert result['saved'] == 1

    @pytest.mark.django_db
    def test_save_articles_creates_new(self, service, raw_news_article_aapl):
        """
        Given: 새 뉴스 1개
        When: _save_articles() 호출
        Then: NewsArticle 생성, saved_count=1
        """
        saved, updated, skipped = service._save_articles([raw_news_article_aapl])

        assert saved == 1
        assert updated == 0
        assert skipped == 0

        from news.models import NewsArticle
        assert NewsArticle.objects.filter(url=raw_news_article_aapl.url).exists()

    @pytest.mark.django_db
    def test_save_articles_updates_existing(self, service, news_article_aapl, raw_news_article_aapl):
        """
        Given: 이미 존재하는 뉴스 (sentiment_score 없음)
        When: sentiment_score 포함한 raw_article로 _save_articles() 호출
        Then: 기존 뉴스 업데이트, updated_count=1
        """
        # 기존 뉴스의 sentiment_score 제거
        news_article_aapl.sentiment_score = None
        news_article_aapl.save()

        # raw_article는 sentiment_score 포함
        raw_news_article_aapl.url = news_article_aapl.url  # 동일 URL

        saved, updated, skipped = service._save_articles([raw_news_article_aapl])

        assert saved == 0
        assert updated == 1
        assert skipped == 0

        # 감성 점수 업데이트 확인
        news_article_aapl.refresh_from_db()
        assert news_article_aapl.sentiment_score is not None

    @pytest.mark.django_db
    def test_save_article_creates_new(self, service, raw_news_article_aapl):
        """
        Given: 존재하지 않는 URL의 뉴스
        When: _save_article() 호출
        Then: 새 NewsArticle 생성, created=True
        """
        article, created = service._save_article(raw_news_article_aapl)

        assert created is True
        assert article.url == raw_news_article_aapl.url
        assert article.title == raw_news_article_aapl.title

    @pytest.mark.django_db
    def test_save_article_updates_existing(self, service, news_article_aapl, raw_news_article_aapl):
        """
        Given: 이미 존재하는 뉴스
        When: _save_article() 호출
        Then: 기존 뉴스 업데이트, created=False
        """
        raw_news_article_aapl.url = news_article_aapl.url

        article, created = service._save_article(raw_news_article_aapl)

        assert created is False
        assert article.pk == news_article_aapl.pk

    @pytest.mark.django_db
    def test_save_entities_creates_new(self, service, news_article_aapl):
        """
        Given: NewsArticle 존재, NewsEntity 없음
        When: _save_entities() 호출
        Then: NewsEntity 생성
        """
        entities_data = [
            {
                'symbol': 'AAPL',
                'entity_name': 'Apple Inc.',
                'entity_type': 'equity',
                'source': 'finnhub',
                'match_score': Decimal('1.00000')
            }
        ]

        service._save_entities(news_article_aapl, entities_data)

        from news.models import NewsEntity
        assert NewsEntity.objects.filter(news=news_article_aapl, symbol='AAPL').exists()

    @pytest.mark.django_db
    def test_save_entities_with_highlights(self, service, news_article_aapl):
        """
        Given: NewsArticle 존재, 하이라이트 포함 엔티티 데이터
        When: _save_entities() 호출
        Then: NewsEntity + EntityHighlight 생성
        """
        entities_data = [
            {
                'symbol': 'AAPL',
                'entity_name': 'Apple Inc.',
                'entity_type': 'equity',
                'source': 'marketaux',
                'match_score': Decimal('0.98765'),
                'sentiment_score': Decimal('0.75'),
                'highlights': [
                    {
                        'text': 'Apple exceeded expectations',
                        'sentiment': Decimal('0.8'),
                        'location': 'title'
                    }
                ]
            }
        ]

        service._save_entities(news_article_aapl, entities_data)

        from news.models import NewsEntity, EntityHighlight
        entity = NewsEntity.objects.get(news=news_article_aapl, symbol='AAPL')
        assert EntityHighlight.objects.filter(news_entity=entity).exists()

    @pytest.mark.django_db
    def test_save_entities_updates_existing(self, service, news_entity_aapl):
        """
        Given: 이미 존재하는 NewsEntity
        When: _save_entities() 호출 (sentiment_score 변경)
        Then: 기존 엔티티 업데이트
        """
        article = news_entity_aapl.news

        entities_data = [
            {
                'symbol': 'AAPL',
                'entity_name': 'Apple Inc.',
                'entity_type': 'equity',
                'source': 'marketaux',
                'match_score': Decimal('0.99000'),
                'sentiment_score': Decimal('0.90')  # 변경된 감성 점수
            }
        ]

        service._save_entities(article, entities_data)

        # 업데이트 확인
        news_entity_aapl.refresh_from_db()
        assert news_entity_aapl.sentiment_score == Decimal('0.90')


# ===== Marker =====

pytestmark = pytest.mark.unit
