"""
News Models Unit Tests

NewsArticle, NewsEntity, EntityHighlight, SentimentHistory 모델 테스트
"""

import pytest
import hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal

from news.models import NewsArticle, NewsEntity, EntityHighlight, SentimentHistory


class TestNewsArticleModel:
    """NewsArticle 모델 테스트"""

    @pytest.mark.django_db
    def test_create_news_article_basic(self):
        """
        Given: 기본 필드만 제공
        When: NewsArticle 생성
        Then: 정상 생성되고 url_hash 자동 생성
        """
        article = NewsArticle.objects.create(
            url='https://example.com/test-article',
            title='Test Article',
            source='Test Source',
            published_at=datetime.now()
        )

        assert article.id is not None
        assert article.url_hash != ''
        assert article.category == 'general'  # 기본값
        assert article.sentiment_source == 'none'  # 기본값
        assert article.is_press_release is False  # 기본값

    @pytest.mark.django_db
    def test_url_hash_generation(self):
        """
        Given: URL 제공
        When: NewsArticle 저장
        Then: URL의 SHA256 해시가 url_hash에 저장됨
        """
        url = 'https://example.com/test-news'
        normalized_url = url.lower().strip()
        expected_hash = hashlib.sha256(normalized_url.encode()).hexdigest()

        article = NewsArticle.objects.create(
            url=url,
            title='Test News',
            source='Test',
            published_at=datetime.now()
        )

        assert article.url_hash == expected_hash

    @pytest.mark.django_db
    def test_url_hash_case_insensitive(self):
        """
        Given: 대소문자만 다른 동일한 URL
        When: 각각 NewsArticle 저장
        Then: 동일한 url_hash 생성 (중복 감지 가능)
        """
        url1 = 'https://EXAMPLE.com/News'
        url2 = 'https://example.com/news'

        article1 = NewsArticle(
            url=url1,
            title='Test 1',
            source='Source',
            published_at=datetime.now()
        )
        article1.save()

        article2 = NewsArticle(
            url=url2,
            title='Test 2',
            source='Source',
            published_at=datetime.now()
        )

        # url이 unique하므로 article2는 저장 불가 (IntegrityError 예상)
        # 하지만 url_hash는 동일함
        assert article1.url_hash == hashlib.sha256(url2.lower().encode()).hexdigest()

    @pytest.mark.django_db
    def test_url_unique_constraint(self):
        """
        Given: 동일한 URL로 두 번째 기사 생성
        When: 저장 시도
        Then: IntegrityError 발생
        """
        from django.db import IntegrityError

        url = 'https://example.com/duplicate-test'

        NewsArticle.objects.create(
            url=url,
            title='First Article',
            source='Source A',
            published_at=datetime.now()
        )

        with pytest.raises(IntegrityError):
            NewsArticle.objects.create(
                url=url,
                title='Second Article',
                source='Source B',
                published_at=datetime.now()
            )

    @pytest.mark.django_db
    def test_sentiment_score_validation(self):
        """
        Given: 범위 밖의 sentiment_score (-1.001)
        When: NewsArticle 저장
        Then: ValidationError 발생
        """
        from django.core.exceptions import ValidationError

        article = NewsArticle(
            url='https://example.com/invalid-sentiment',
            title='Test',
            source='Source',
            published_at=datetime.now(),
            sentiment_score=Decimal('-1.001')  # 범위 밖
        )

        with pytest.raises(ValidationError):
            article.full_clean()

    @pytest.mark.django_db
    def test_sentiment_score_valid_range(self):
        """
        Given: 유효한 sentiment_score 범위 (-1.000 ~ +1.000)
        When: NewsArticle 저장
        Then: 정상 저장
        """
        article = NewsArticle.objects.create(
            url='https://example.com/valid-sentiment',
            title='Test',
            source='Source',
            published_at=datetime.now(),
            sentiment_score=Decimal('0.750')
        )

        assert article.sentiment_score == Decimal('0.750')

    @pytest.mark.django_db
    def test_str_representation(self):
        """
        Given: NewsArticle 인스턴스
        When: str() 호출
        Then: "제목[:50] (출처)" 형식 반환
        """
        article = NewsArticle.objects.create(
            url='https://example.com/test',
            title='This is a very long article title that exceeds fifty characters for testing',
            source='Bloomberg',
            published_at=datetime.now()
        )

        str_repr = str(article)

        assert 'This is a very long article title that exceeds' in str_repr
        assert '(Bloomberg)' in str_repr
        assert len(str_repr) <= 65  # 제목 50자 + " " + 괄호 + 출처(최대 15자)

    @pytest.mark.django_db
    def test_ordering_by_published_at(self):
        """
        Given: 여러 NewsArticle (발행 일시 다름)
        When: 쿼리 조회
        Then: 최신순 정렬
        """
        now = datetime.now()

        article1 = NewsArticle.objects.create(
            url='https://example.com/old',
            title='Old Article',
            source='Source',
            published_at=now - timedelta(days=2)
        )

        article2 = NewsArticle.objects.create(
            url='https://example.com/new',
            title='New Article',
            source='Source',
            published_at=now
        )

        articles = list(NewsArticle.objects.all())

        assert articles[0] == article2  # 최신 먼저
        assert articles[1] == article1


class TestNewsEntityModel:
    """NewsEntity 모델 테스트"""

    @pytest.mark.django_db
    def test_create_news_entity(self, news_article_aapl):
        """
        Given: NewsArticle 존재
        When: NewsEntity 생성
        Then: 정상 생성 및 ForeignKey 연결
        """
        entity = NewsEntity.objects.create(
            news=news_article_aapl,
            symbol='AAPL',
            entity_name='Apple Inc.',
            entity_type='equity',
            source='finnhub',
            match_score=Decimal('1.00000')
        )

        assert entity.news == news_article_aapl
        assert entity.symbol == 'AAPL'
        assert entity.entity_type == 'equity'
        assert entity.match_score == Decimal('1.00000')

    @pytest.mark.django_db
    def test_unique_together_constraint(self, news_article_aapl):
        """
        Given: 동일한 (news, symbol) 조합으로 두 번째 NewsEntity 생성
        When: 저장 시도
        Then: IntegrityError 발생
        """
        from django.db import IntegrityError

        NewsEntity.objects.create(
            news=news_article_aapl,
            symbol='AAPL',
            entity_name='Apple Inc.',
            entity_type='equity',
            source='finnhub'
        )

        with pytest.raises(IntegrityError):
            NewsEntity.objects.create(
                news=news_article_aapl,
                symbol='AAPL',  # 동일한 symbol
                entity_name='Apple',
                entity_type='equity',
                source='marketaux'
            )

    @pytest.mark.django_db
    def test_multiple_entities_for_one_article(self, news_article_aapl):
        """
        Given: 하나의 NewsArticle
        When: 여러 종목의 NewsEntity 생성
        Then: M:N 관계 정상 동작
        """
        entity1 = NewsEntity.objects.create(
            news=news_article_aapl,
            symbol='AAPL',
            entity_name='Apple Inc.',
            entity_type='equity',
            source='finnhub'
        )

        entity2 = NewsEntity.objects.create(
            news=news_article_aapl,
            symbol='MSFT',
            entity_name='Microsoft Corp.',
            entity_type='equity',
            source='finnhub'
        )

        entities = news_article_aapl.entities.all()

        assert entities.count() == 2
        assert entity1 in entities
        assert entity2 in entities

    @pytest.mark.django_db
    def test_sentiment_score_per_entity(self, news_article_aapl):
        """
        Given: 동일 기사에 여러 종목
        When: 각 종목별로 다른 sentiment_score 설정
        Then: 엔티티별 감성 점수 독립적으로 저장
        """
        entity_aapl = NewsEntity.objects.create(
            news=news_article_aapl,
            symbol='AAPL',
            entity_name='Apple Inc.',
            entity_type='equity',
            sentiment_score=Decimal('0.80'),
            source='marketaux'
        )

        entity_msft = NewsEntity.objects.create(
            news=news_article_aapl,
            symbol='MSFT',
            entity_name='Microsoft Corp.',
            entity_type='equity',
            sentiment_score=Decimal('-0.20'),
            source='marketaux'
        )

        assert entity_aapl.sentiment_score == Decimal('0.80')
        assert entity_msft.sentiment_score == Decimal('-0.20')

    @pytest.mark.django_db
    def test_cascade_delete(self, news_article_aapl):
        """
        Given: NewsEntity가 연결된 NewsArticle
        When: NewsArticle 삭제
        Then: 연결된 NewsEntity도 함께 삭제 (CASCADE)
        """
        entity = NewsEntity.objects.create(
            news=news_article_aapl,
            symbol='AAPL',
            entity_name='Apple Inc.',
            entity_type='equity',
            source='finnhub'
        )

        entity_id = entity.id
        news_article_aapl.delete()

        assert not NewsEntity.objects.filter(id=entity_id).exists()


class TestEntityHighlightModel:
    """EntityHighlight 모델 테스트"""

    @pytest.mark.django_db
    def test_create_entity_highlight(self, news_entity_aapl):
        """
        Given: NewsEntity 존재
        When: EntityHighlight 생성
        Then: 정상 생성 및 ForeignKey 연결
        """
        highlight = EntityHighlight.objects.create(
            news_entity=news_entity_aapl,
            highlight_text='Apple exceeded revenue expectations',
            sentiment=Decimal('0.85'),
            location='title'
        )

        assert highlight.news_entity == news_entity_aapl
        assert highlight.highlight_text == 'Apple exceeded revenue expectations'
        assert highlight.sentiment == Decimal('0.85')
        assert highlight.location == 'title'

    @pytest.mark.django_db
    def test_multiple_highlights_per_entity(self, news_entity_aapl):
        """
        Given: 하나의 NewsEntity
        When: 여러 EntityHighlight 생성
        Then: 모든 하이라이트 연결됨
        """
        highlight1 = EntityHighlight.objects.create(
            news_entity=news_entity_aapl,
            highlight_text='Revenue up 20%',
            sentiment=Decimal('0.75'),
            location='title'
        )

        highlight2 = EntityHighlight.objects.create(
            news_entity=news_entity_aapl,
            highlight_text='Profit margins improved',
            sentiment=Decimal('0.65'),
            location='main_text'
        )

        highlights = news_entity_aapl.highlights.all()

        assert highlights.count() == 2
        # ordering = ['-sentiment']이므로 높은 감성 점수가 먼저
        assert list(highlights) == [highlight1, highlight2]

    @pytest.mark.django_db
    def test_ordering_by_sentiment_desc(self, news_entity_aapl):
        """
        Given: 여러 EntityHighlight (감성 점수 다름)
        When: 쿼리 조회
        Then: 감성 점수 내림차순 정렬
        """
        h1 = EntityHighlight.objects.create(
            news_entity=news_entity_aapl,
            highlight_text='Low sentiment',
            sentiment=Decimal('0.30'),
            location='main_text'
        )

        h2 = EntityHighlight.objects.create(
            news_entity=news_entity_aapl,
            highlight_text='High sentiment',
            sentiment=Decimal('0.90'),
            location='title'
        )

        h3 = EntityHighlight.objects.create(
            news_entity=news_entity_aapl,
            highlight_text='Medium sentiment',
            sentiment=Decimal('0.60'),
            location='main_text'
        )

        highlights = list(EntityHighlight.objects.all())

        assert highlights == [h2, h3, h1]  # 감성 점수 내림차순


class TestSentimentHistoryModel:
    """SentimentHistory 모델 테스트"""

    @pytest.mark.django_db
    def test_create_sentiment_history(self):
        """
        Given: 종목 심볼 및 날짜
        When: SentimentHistory 생성
        Then: 정상 생성 및 집계 데이터 저장
        """
        history = SentimentHistory.objects.create(
            symbol='AAPL',
            date=date(2024, 12, 8),
            avg_sentiment=Decimal('0.65'),
            news_count=10,
            positive_count=7,
            negative_count=2,
            neutral_count=1
        )

        assert history.symbol == 'AAPL'
        assert history.date == date(2024, 12, 8)
        assert history.avg_sentiment == Decimal('0.65')
        assert history.news_count == 10
        assert history.positive_count == 7
        assert history.negative_count == 2
        assert history.neutral_count == 1

    @pytest.mark.django_db
    def test_unique_together_symbol_date(self):
        """
        Given: 동일한 (symbol, date) 조합으로 두 번째 SentimentHistory 생성
        When: 저장 시도
        Then: IntegrityError 발생
        """
        from django.db import IntegrityError

        SentimentHistory.objects.create(
            symbol='AAPL',
            date=date(2024, 12, 8),
            avg_sentiment=Decimal('0.50'),
            news_count=5
        )

        with pytest.raises(IntegrityError):
            SentimentHistory.objects.create(
                symbol='AAPL',
                date=date(2024, 12, 8),  # 동일한 날짜
                avg_sentiment=Decimal('0.60'),
                news_count=8
            )

    @pytest.mark.django_db
    def test_ordering_by_date_desc(self):
        """
        Given: 여러 SentimentHistory (날짜 다름)
        When: 쿼리 조회
        Then: 최신 날짜순 정렬
        """
        h1 = SentimentHistory.objects.create(
            symbol='AAPL',
            date=date(2024, 12, 5),
            avg_sentiment=Decimal('0.50'),
            news_count=5
        )

        h2 = SentimentHistory.objects.create(
            symbol='AAPL',
            date=date(2024, 12, 8),
            avg_sentiment=Decimal('0.60'),
            news_count=8
        )

        h3 = SentimentHistory.objects.create(
            symbol='AAPL',
            date=date(2024, 12, 6),
            avg_sentiment=Decimal('0.55'),
            news_count=6
        )

        histories = list(SentimentHistory.objects.all())

        assert histories == [h2, h3, h1]  # 최신 날짜 먼저

    @pytest.mark.django_db
    def test_sentiment_count_sum_equals_news_count(self):
        """
        Given: SentimentHistory 생성
        When: positive + negative + neutral count 합산
        Then: news_count와 일치
        """
        history = SentimentHistory.objects.create(
            symbol='MSFT',
            date=date(2024, 12, 8),
            avg_sentiment=Decimal('0.30'),
            news_count=15,
            positive_count=8,
            negative_count=4,
            neutral_count=3
        )

        total = history.positive_count + history.negative_count + history.neutral_count

        assert total == history.news_count


# ===== Marker =====

pytestmark = pytest.mark.unit
