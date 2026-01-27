"""
News App Test Fixtures

뉴스 기능 테스트를 위한 공통 fixtures
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from news.providers.base import RawNewsArticle


# ===== Fixture: Sample Finnhub Response =====

@pytest.fixture
def sample_finnhub_response():
    """Finnhub API 응답 샘플"""
    return [
        {
            'id': 123456,
            'headline': 'Apple Announces Record Q4 Earnings',
            'summary': 'Apple Inc. reported record quarterly revenue...',
            'url': 'https://finance.yahoo.com/news/apple-earnings-q4-2024-123456.html',
            'source': 'Yahoo Finance',
            'datetime': 1700000000,  # Unix timestamp
            'image': 'https://example.com/images/apple-earnings.jpg',
            'related': 'AAPL',
            'category': 'company news'
        },
        {
            'id': 123457,
            'headline': 'Tech Stocks Rally on Fed Comments',
            'summary': 'Technology stocks surged following...',
            'url': 'https://reuters.com/tech-rally-fed-123457',
            'source': 'Reuters',
            'datetime': 1699900000,
            'image': 'https://example.com/images/tech-rally.jpg',
            'related': 'MSFT',
            'category': 'general'
        }
    ]


@pytest.fixture
def sample_finnhub_single_article():
    """단일 Finnhub 기사"""
    return {
        'id': 999999,
        'headline': 'Tesla Stock Jumps on Delivery Numbers',
        'summary': 'Tesla shares rose 5% after reporting...',
        'url': 'https://bloomberg.com/tesla-delivery-999999',
        'source': 'Bloomberg',
        'datetime': 1700100000,
        'image': 'https://example.com/images/tesla.jpg',
        'related': 'TSLA',
        'category': 'company news'
    }


# ===== Fixture: Sample Marketaux Response =====

@pytest.fixture
def sample_marketaux_response():
    """Marketaux API 응답 샘플"""
    return {
        'data': [
            {
                'uuid': 'abc-123-def-456',
                'title': 'Apple Surpasses Expectations with iPhone Sales',
                'description': 'Apple Inc. reported stronger-than-expected iPhone sales...',
                'url': 'https://cnbc.com/apple-iphone-sales-abc123',
                'image_url': 'https://example.com/images/apple-iphone.jpg',
                'published_at': '2024-12-08T10:30:00.000000Z',
                'source': 'CNBC',
                'language': 'en',
                'entities': [
                    {
                        'symbol': 'AAPL',
                        'name': 'Apple Inc.',
                        'exchange': 'NASDAQ',
                        'exchange_long': 'NASDAQ Stock Exchange',
                        'country': 'us',
                        'type': 'equity',
                        'industry': 'Technology',
                        'match_score': 0.98765,
                        'sentiment_score': 0.75,
                        'highlights': [
                            {
                                'highlight': 'Apple exceeded revenue expectations',
                                'sentiment': 0.8,
                                'highlighted_in': 'title'
                            },
                            {
                                'highlight': 'iPhone sales growth impressive',
                                'sentiment': 0.7,
                                'highlighted_in': 'main_text'
                            }
                        ]
                    }
                ]
            },
            {
                'uuid': 'xyz-789-uvw-012',
                'title': 'Microsoft Cloud Revenue Disappoints',
                'description': 'Microsoft Azure growth slowed in Q4...',
                'url': 'https://wsj.com/microsoft-cloud-xyz789',
                'image_url': 'https://example.com/images/microsoft-cloud.jpg',
                'published_at': '2024-12-08T09:15:00.000000Z',
                'source': 'Wall Street Journal',
                'language': 'en',
                'entities': [
                    {
                        'symbol': 'MSFT',
                        'name': 'Microsoft Corporation',
                        'exchange': 'NASDAQ',
                        'exchange_long': 'NASDAQ Stock Exchange',
                        'country': 'us',
                        'type': 'equity',
                        'industry': 'Technology',
                        'match_score': 0.95432,
                        'sentiment_score': -0.35,
                        'highlights': [
                            {
                                'highlight': 'Azure growth disappoints investors',
                                'sentiment': -0.5,
                                'highlighted_in': 'title'
                            }
                        ]
                    }
                ]
            }
        ],
        'meta': {
            'found': 2,
            'limit': 3,
            'page': 1
        }
    }


@pytest.fixture
def sample_marketaux_single_article():
    """단일 Marketaux 기사"""
    return {
        'uuid': 'single-test-uuid',
        'title': 'Google Announces AI Breakthrough',
        'description': 'Google unveiled new AI technology...',
        'url': 'https://techcrunch.com/google-ai-breakthrough',
        'image_url': 'https://example.com/images/google-ai.jpg',
        'published_at': '2024-12-08T14:00:00.000000Z',
        'source': 'TechCrunch',
        'language': 'en',
        'entities': [
            {
                'symbol': 'GOOGL',
                'name': 'Alphabet Inc.',
                'exchange': 'NASDAQ',
                'country': 'us',
                'type': 'equity',
                'industry': 'Technology',
                'match_score': 0.99,
                'sentiment_score': 0.85,
                'highlights': []
            }
        ]
    }


# ===== Fixture: RawNewsArticle Instances =====

@pytest.fixture
def raw_news_article_aapl():
    """Apple 뉴스 RawNewsArticle 인스턴스"""
    return RawNewsArticle(
        url='https://example.com/apple-news-1',
        title='Apple Stock Hits All-Time High',
        summary='Apple shares reached a new record...',
        source='Bloomberg',
        published_at=datetime(2024, 12, 8, 10, 0, 0),
        image_url='https://example.com/images/apple.jpg',
        language='en',
        category='company',
        provider_id='123456',  # Finnhub는 정수 ID
        provider_name='finnhub',
        sentiment_score=Decimal('0.65'),
        sentiment_source='marketaux',
        entities=[
            {
                'symbol': 'AAPL',
                'entity_name': 'Apple Inc.',
                'entity_type': 'equity',
                'source': 'finnhub',
                'match_score': Decimal('1.00000')
            }
        ],
        is_press_release=False
    )


@pytest.fixture
def raw_news_article_msft():
    """Microsoft 뉴스 RawNewsArticle 인스턴스"""
    return RawNewsArticle(
        url='https://example.com/microsoft-news-1',
        title='Microsoft Expands Cloud Services',
        summary='Microsoft announced new Azure features...',
        source='Reuters',
        published_at=datetime(2024, 12, 8, 11, 0, 0),
        image_url='https://example.com/images/microsoft.jpg',
        language='en',
        category='company',
        provider_id='abc-123-def-456',  # Marketaux는 UUID 문자열
        provider_name='marketaux',
        sentiment_score=Decimal('0.45'),
        sentiment_source='marketaux',
        entities=[
            {
                'symbol': 'MSFT',
                'entity_name': 'Microsoft Corporation',
                'entity_type': 'equity',
                'exchange': 'NASDAQ',
                'country': 'us',
                'industry': 'Technology',
                'match_score': Decimal('0.95000'),
                'sentiment_score': Decimal('0.45'),
                'source': 'marketaux',
                'highlights': [
                    {
                        'text': 'Microsoft expands cloud infrastructure',
                        'sentiment': Decimal('0.5'),
                        'location': 'title'
                    }
                ]
            }
        ],
        is_press_release=False
    )


@pytest.fixture
def duplicate_news_articles():
    """중복 제거 테스트용 뉴스 리스트"""
    now = datetime.now()

    return [
        # 동일 URL (정규화 후)
        RawNewsArticle(
            url='https://example.com/news/1',
            title='Breaking News 1',
            summary='Summary 1',
            source='Source A',
            published_at=now,
            image_url='',
            language='en',
            category='general',
            provider_id='dup-1',
            provider_name='finnhub',
            sentiment_score=None,
            sentiment_source='none',
            entities=[],
            is_press_release=False
        ),
        RawNewsArticle(
            url='https://EXAMPLE.COM/news/1',  # 대소문자 다름
            title='Breaking News 1',
            summary='Summary 1',
            source='Source A',
            published_at=now,
            image_url='',
            language='en',
            category='general',
            provider_id='dup-1',
            provider_name='finnhub',
            sentiment_score=None,
            sentiment_source='none',
            entities=[],
            is_press_release=False
        ),
        # 유사한 제목
        RawNewsArticle(
            url='https://different.com/news/2',
            title='Apple Announces Record Quarterly Earnings',
            summary='Summary 2',
            source='Source B',
            published_at=now,
            image_url='',
            language='en',
            category='company',
            provider_id='dup-2',
            provider_name='finnhub',
            sentiment_score=None,
            sentiment_source='none',
            entities=[],
            is_press_release=False
        ),
        RawNewsArticle(
            url='https://another.com/news/3',
            title='Apple Announces Record Quarterly Earnings Results',  # 거의 동일한 제목
            summary='Summary 3',
            source='Source C',
            published_at=now,
            image_url='',
            language='en',
            category='company',
            provider_id='dup-3',
            provider_name='marketaux',
            sentiment_score=None,
            sentiment_source='none',
            entities=[],
            is_press_release=False
        ),
        # 완전히 다른 뉴스
        RawNewsArticle(
            url='https://unique.com/news/4',
            title='Tesla Unveils New Model',
            summary='Summary 4',
            source='Source D',
            published_at=now,
            image_url='',
            language='en',
            category='company',
            provider_id='unique-1',
            provider_name='finnhub',
            sentiment_score=None,
            sentiment_source='none',
            entities=[],
            is_press_release=False
        )
    ]


# ===== Fixture: Django Models =====

@pytest.fixture
@pytest.mark.django_db
def news_article_aapl():
    """DB에 저장된 Apple 뉴스"""
    from news.models import NewsArticle
    from django.utils import timezone

    return NewsArticle.objects.create(
        url='https://example.com/apple-earnings-2024',
        title='Apple Reports Strong Q4 Earnings',
        summary='Apple Inc. reported quarterly revenue of $120 billion...',
        source='Bloomberg',
        published_at=timezone.now(),  # 현재 시간 (timezone-aware)
        image_url='https://example.com/images/apple-q4.jpg',
        language='en',
        category='company',
        finnhub_id=999001,
        sentiment_score=Decimal('0.72'),
        sentiment_source='marketaux',
        is_press_release=False
    )


@pytest.fixture
@pytest.mark.django_db
def news_entity_aapl(news_article_aapl):
    """DB에 저장된 Apple NewsEntity"""
    from news.models import NewsEntity

    return NewsEntity.objects.create(
        news=news_article_aapl,
        symbol='AAPL',
        entity_name='Apple Inc.',
        entity_type='equity',
        exchange='NASDAQ',
        country='us',
        industry='Technology',
        match_score=Decimal('0.98765'),
        sentiment_score=Decimal('0.75'),
        source='marketaux'
    )


@pytest.fixture
@pytest.mark.django_db
def sentiment_history_aapl():
    """DB에 저장된 Apple SentimentHistory"""
    from news.models import SentimentHistory
    from django.utils import timezone

    return SentimentHistory.objects.create(
        symbol='AAPL',
        date=timezone.now().date(),
        avg_sentiment=Decimal('0.65'),
        news_count=10,
        positive_count=7,
        negative_count=1,
        neutral_count=2
    )


# ===== Marker =====

pytestmark = pytest.mark.unit
