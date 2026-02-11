"""
뉴스 Entity 중복 방지 테스트

버그: 모든 종목에 동일한 뉴스가 표시되는 문제 재발 방지
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

from news.providers.finnhub import FinnhubNewsProvider
from news.providers.marketaux import MarketauxNewsProvider
from news.services.aggregator import NewsAggregatorService
from news.models import NewsArticle, NewsEntity


class TestFinnhubEntityMapping:
    """Finnhub Provider Entity 매핑 테스트"""

    @pytest.fixture
    def provider(self):
        return FinnhubNewsProvider(api_key="test_key")

    def test_parse_article_uses_related_field(self, provider):
        """
        API 응답의 related 필드를 사용해야 함 (요청 symbol 아님)

        시나리오: TSLA 뉴스 요청했지만 실제로는 NVDA 관련 뉴스 반환
        """
        item = {
            'headline': 'Nvidia announces new AI chip',
            'related': 'NVDA',  # 실제 관련 종목
            'summary': 'Nvidia unveils...',
            'datetime': 1605543180,
            'source': 'Reuters',
            'url': 'https://example.com/nvda-ai-chip'
        }

        # TSLA로 요청했지만
        article = provider._parse_article(item, symbol='TSLA')

        # Entity는 NVDA여야 함
        assert len(article.entities) == 1
        assert article.entities[0]['symbol'] == 'NVDA'
        assert article.entities[0]['symbol'] != 'TSLA'

    def test_parse_article_no_entity_if_no_related(self, provider):
        """
        related 필드가 없으면 entity 없어야 함
        """
        item = {
            'headline': 'General market news',
            'related': '',  # 관련 종목 없음
            'summary': 'Market overview...',
            'datetime': 1605543180,
            'source': 'Bloomberg',
            'url': 'https://example.com/market-news'
        }

        article = provider._parse_article(item, symbol='AAPL')

        # Entity 없어야 함
        assert len(article.entities) == 0

    def test_parse_article_ignores_request_symbol(self, provider):
        """
        요청 파라미터 symbol을 무시해야 함
        """
        item = {
            'headline': 'Tesla production update',
            'related': 'TSLA',
            'summary': 'Tesla factory...',
            'datetime': 1605543180,
            'source': 'Reuters',
            'url': 'https://example.com/tsla-production'
        }

        # AAPL로 요청
        article = provider._parse_article(item, symbol='AAPL')

        # Entity는 related 필드(TSLA)를 사용
        assert len(article.entities) == 1
        assert article.entities[0]['symbol'] == 'TSLA'


class TestAggregatorEntityDeduplication:
    """Aggregator Entity 중복 방지 테스트"""

    @pytest.fixture
    def service(self):
        return NewsAggregatorService()

    @pytest.mark.django_db
    def test_no_duplicate_entities_on_multiple_saves(self, service):
        """
        같은 뉴스를 여러 번 저장해도 entity 중복 없어야 함

        시나리오: Nvidia 뉴스를 TSLA, AAPL, GOOGL 조회 시마다 저장 시도
        """
        from news.providers.base import RawNewsArticle

        # 첫 번째 저장 (NVDA entity)
        raw_article = RawNewsArticle(
            url='https://example.com/nvda-news',
            title='Nvidia AI chip',
            summary='Nvidia unveils...',
            source='Reuters',
            published_at=datetime.now(),
            image_url='',
            language='en',
            category='company',
            provider_id='123',
            provider_name='finnhub',
            sentiment_score=None,
            sentiment_source='none',
            entities=[{
                'symbol': 'NVDA',
                'entity_name': 'NVIDIA Corporation',
                'entity_type': 'equity',
                'source': 'finnhub',
                'match_score': Decimal('1.00000')
            }],
            is_press_release=False
        )

        saved_count, _, _ = service._save_articles([raw_article])
        assert saved_count == 1

        # 같은 URL로 두 번째 저장 시도 (다른 entity)
        raw_article.entities = [{
            'symbol': 'TSLA',
            'entity_name': 'Tesla Inc',
            'entity_type': 'equity',
            'source': 'finnhub',
            'match_score': Decimal('1.00000')
        }]

        saved_count, updated_count, _ = service._save_articles([raw_article])
        assert saved_count == 0  # 새로 저장 안됨
        assert updated_count == 1  # 업데이트만

        # Entity는 NVDA 1개만 있어야 함 (TSLA 추가 안됨)
        article = NewsArticle.objects.get(url='https://example.com/nvda-news')
        entities = article.entities.all()

        assert entities.count() == 1
        assert entities.first().symbol == 'NVDA'

    @pytest.mark.django_db
    def test_existing_article_entity_unchanged(self, service):
        """
        기존 뉴스의 entity는 변경되지 않아야 함
        """
        from news.providers.base import RawNewsArticle

        # 초기 저장
        raw_article = RawNewsArticle(
            url='https://example.com/apple-news',
            title='Apple earnings beat',
            summary='Apple reports...',
            source='Bloomberg',
            published_at=datetime.now(),
            image_url='',
            language='en',
            category='company',
            provider_id='456',
            provider_name='finnhub',
            sentiment_score=None,
            sentiment_source='none',
            entities=[{
                'symbol': 'AAPL',
                'entity_name': 'Apple Inc',
                'entity_type': 'equity',
                'source': 'finnhub',
                'match_score': Decimal('1.00000')
            }],
            is_press_release=False
        )

        service._save_articles([raw_article])

        # 원본 entity 확인
        article = NewsArticle.objects.get(url='https://example.com/apple-news')
        original_entities = list(article.entities.values('symbol'))

        # 다른 entity로 재저장 시도
        raw_article.entities = [{
            'symbol': 'GOOGL',
            'entity_name': 'Alphabet Inc',
            'entity_type': 'equity',
            'source': 'finnhub',
            'match_score': Decimal('1.00000')
        }]

        service._save_articles([raw_article])

        # Entity 변경 없어야 함
        article.refresh_from_db()
        current_entities = list(article.entities.values('symbol'))

        assert current_entities == original_entities
        assert current_entities == [{'symbol': 'AAPL'}]


class TestNewsAPIViews:
    """뉴스 API 뷰 테스트"""

    @pytest.mark.django_db
    def test_stock_news_returns_only_related_news(self):
        """
        종목별 뉴스 조회 시 해당 종목 뉴스만 반환
        """
        # AAPL 뉴스 생성
        aapl_article = NewsArticle.objects.create(
            url='https://example.com/aapl-news',
            title='Apple earnings',
            summary='Apple reports...',
            source='Reuters',
            published_at=datetime.now(),
            language='en',
            category='company'
        )
        NewsEntity.objects.create(
            news=aapl_article,
            symbol='AAPL',
            entity_name='Apple Inc',
            entity_type='equity',
            source='finnhub'
        )

        # TSLA 뉴스 생성
        tsla_article = NewsArticle.objects.create(
            url='https://example.com/tsla-news',
            title='Tesla production',
            summary='Tesla factory...',
            source='Reuters',
            published_at=datetime.now(),
            language='en',
            category='company'
        )
        NewsEntity.objects.create(
            news=tsla_article,
            symbol='TSLA',
            entity_name='Tesla Inc',
            entity_type='equity',
            source='finnhub'
        )

        # AAPL 뉴스 조회
        from django.test import Client
        client = Client()
        response = client.get('/api/v1/news/stock/AAPL/')

        assert response.status_code == 200
        data = response.json()

        # AAPL 뉴스만 반환
        assert data['count'] == 1
        assert data['articles'][0]['title'] == 'Apple earnings'

        # TSLA 뉴스는 포함 안됨
        titles = [a['title'] for a in data['articles']]
        assert 'Tesla production' not in titles


# Integration Test
@pytest.mark.django_db
class TestNewsSystemIntegration:
    """뉴스 시스템 통합 테스트"""

    @patch('news.providers.finnhub.requests.get')
    def test_multiple_symbol_fetches_no_cross_contamination(self, mock_get):
        """
        여러 종목 뉴스 수집 시 교차 오염 없음 확인

        시나리오:
        1. TSLA 뉴스 수집 (실제로는 NVDA 뉴스 반환)
        2. AAPL 뉴스 수집 (실제로는 AAPL 뉴스 반환)
        3. 각 종목 조회 시 올바른 뉴스만 표시
        """
        # Mock Finnhub API responses
        def mock_response(*args, **kwargs):
            params = kwargs.get('params', {})
            symbol = params.get('symbol', '')

            response = Mock()
            response.status_code = 200

            if symbol == 'TSLA':
                # TSLA 요청이지만 NVDA 뉴스 반환
                response.json.return_value = [{
                    'headline': 'Nvidia AI chip',
                    'related': 'NVDA',
                    'summary': 'Nvidia unveils...',
                    'datetime': 1605543180,
                    'source': 'Reuters',
                    'url': 'https://example.com/nvda-news',
                    'id': 123
                }]
            elif symbol == 'AAPL':
                # AAPL 뉴스 반환
                response.json.return_value = [{
                    'headline': 'Apple earnings',
                    'related': 'AAPL',
                    'summary': 'Apple reports...',
                    'datetime': 1605543180,
                    'source': 'Bloomberg',
                    'url': 'https://example.com/aapl-news',
                    'id': 456
                }]

            return response

        mock_get.side_effect = mock_response

        # 서비스 실행
        service = NewsAggregatorService()

        # TSLA 뉴스 수집
        result1 = service.fetch_and_save_company_news('TSLA', days=7, use_marketaux=False)
        assert result1['saved'] == 1

        # AAPL 뉴스 수집
        result2 = service.fetch_and_save_company_news('AAPL', days=7, use_marketaux=False)
        assert result2['saved'] == 1

        # 검증: TSLA 조회 시 NVDA 뉴스만
        tsla_news = NewsArticle.objects.filter(entities__symbol='TSLA')
        assert tsla_news.count() == 0  # TSLA entity 없음

        nvda_news = NewsArticle.objects.filter(entities__symbol='NVDA')
        assert nvda_news.count() == 1  # NVDA entity 있음
        assert 'Nvidia' in nvda_news.first().title

        # 검증: AAPL 조회 시 AAPL 뉴스만
        aapl_news = NewsArticle.objects.filter(entities__symbol='AAPL')
        assert aapl_news.count() == 1
        assert 'Apple' in aapl_news.first().title

        # 교집합 없어야 함
        common = nvda_news & aapl_news
        assert common.count() == 0
