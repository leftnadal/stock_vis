"""
Market Feed Service + API 테스트

커버 범위:
- MarketFeedService.get_feed()
- MarketFeedService._get_latest_keywords()
- MarketFeedService._enrich_keywords_with_news()
- MarketFeedService._get_market_context()
- InterestOptionsService.get_options()
- GET /api/v1/news/market-feed/
- GET /api/v1/news/interest-options/
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.utils import timezone
from rest_framework.test import APIClient

from news.models import DailyNewsKeyword, NewsArticle, NewsEntity
from news.services.market_feed import MarketFeedService
from news.services.interest_options import InterestOptionsService, PREDEFINED_THEMES


# ===== MarketFeedService 단위 테스트 =====

@pytest.mark.django_db
class TestMarketFeedServiceNoData:
    """데이터가 없을 때 MarketFeedService 동작 테스트"""

    def setup_method(self):
        self.service = MarketFeedService()

    def test_get_feed_returns_fallback_when_no_keywords(self):
        """
        Given: DailyNewsKeyword 레코드가 전혀 없음
        When: get_feed() 호출
        Then: is_fallback=True, keywords=[], fallback_message='아직 분석된 키워드가 없습니다'
        """
        result = self.service.get_feed()

        assert result['is_fallback'] is True
        assert result['briefing']['keywords'] == []
        assert result['briefing']['total_news_count'] == 0
        assert result['briefing']['llm_model'] is None
        assert result['fallback_message'] == '아직 분석된 키워드가 없습니다'

    def test_get_feed_response_structure_when_no_data(self):
        """
        Given: 데이터 없음
        When: get_feed() 호출
        Then: 응답에 필수 키 포함
        """
        result = self.service.get_feed()

        assert 'date' in result
        assert 'is_fallback' in result
        assert 'fallback_message' in result
        assert 'briefing' in result
        assert 'market_context' in result
        assert 'keywords' in result['briefing']
        assert 'top_sectors' in result['market_context']
        assert 'hot_movers' in result['market_context']

    def test_get_feed_ignores_pending_status_keywords(self):
        """
        Given: status='pending'인 오늘 날짜 키워드
        When: get_feed() 호출
        Then: pending 레코드는 무시하고 fallback 반환
        """
        today = timezone.now().date()
        DailyNewsKeyword.objects.create(
            date=today,
            keywords=[],
            status='pending',
        )

        result = self.service.get_feed()

        assert result['is_fallback'] is True
        assert result['briefing']['keywords'] == []

    def test_get_feed_ignores_failed_status_keywords(self):
        """
        Given: status='failed'인 오늘 날짜 키워드
        When: get_feed() 호출
        Then: failed 레코드는 무시하고 fallback 반환
        """
        today = timezone.now().date()
        DailyNewsKeyword.objects.create(
            date=today,
            keywords=[{'text': '실패 키워드', 'sentiment': 'neutral'}],
            status='failed',
        )

        result = self.service.get_feed()

        assert result['is_fallback'] is True


@pytest.mark.django_db
class TestMarketFeedServiceWithTodayKeywords:
    """오늘 날짜 완료된 키워드가 있을 때 MarketFeedService 동작 테스트"""

    def setup_method(self):
        self.service = MarketFeedService()

    def _create_today_keyword(self, keywords=None, total_news_count=50):
        """오늘 날짜 completed 키워드 레코드 생성 헬퍼"""
        today = timezone.now().date()
        if keywords is None:
            keywords = [
                {
                    'text': 'AI 반도체',
                    'sentiment': 'positive',
                    'related_symbols': ['NVDA'],
                    'importance': 0.9,
                    'reason': '수요 급증',
                }
            ]
        return DailyNewsKeyword.objects.create(
            date=today,
            keywords=keywords,
            total_news_count=total_news_count,
            status='completed',
            llm_model='gemini-2.5-flash',
        )

    def test_get_feed_returns_non_fallback_for_today_keywords(self):
        """
        Given: 오늘 completed 키워드
        When: get_feed() 호출
        Then: is_fallback=False, fallback_message=None
        """
        self._create_today_keyword()

        result = self.service.get_feed()

        assert result['is_fallback'] is False
        assert result['fallback_message'] is None

    def test_get_feed_date_matches_today(self):
        """
        Given: 오늘 completed 키워드
        When: get_feed() 호출
        Then: date 필드가 오늘 날짜
        """
        today = timezone.now().date()
        self._create_today_keyword()

        result = self.service.get_feed()

        assert result['date'] == str(today)

    def test_get_feed_keyword_content_preserved(self):
        """
        Given: 키워드에 text, sentiment, reason 포함
        When: get_feed() 호출
        Then: enriched 키워드에 동일 내용 유지됨
        """
        self._create_today_keyword(keywords=[
            {
                'text': 'AI 반도체',
                'sentiment': 'positive',
                'related_symbols': ['NVDA'],
                'importance': 0.9,
                'reason': '수요 급증',
            }
        ])

        result = self.service.get_feed()
        kw = result['briefing']['keywords'][0]

        assert kw['text'] == 'AI 반도체'
        assert kw['sentiment'] == 'positive'
        assert kw['reason'] == '수요 급증'
        assert kw['importance'] == 0.9
        assert 'NVDA' in kw['related_symbols']

    def test_get_feed_enriched_keyword_has_news_fields(self):
        """
        Given: 오늘 completed 키워드
        When: get_feed() 호출
        Then: enriched 키워드에 news_count, headlines 필드 포함
        """
        self._create_today_keyword()

        result = self.service.get_feed()
        kw = result['briefing']['keywords'][0]

        assert 'news_count' in kw
        assert 'headlines' in kw
        assert isinstance(kw['news_count'], int)
        assert isinstance(kw['headlines'], list)

    def test_get_feed_total_news_count_from_keyword_obj(self):
        """
        Given: total_news_count=50인 키워드
        When: get_feed() 호출
        Then: briefing.total_news_count == 50
        """
        self._create_today_keyword(total_news_count=50)

        result = self.service.get_feed()

        assert result['briefing']['total_news_count'] == 50

    def test_get_feed_llm_model_included(self):
        """
        Given: llm_model='gemini-2.5-flash'인 키워드
        When: get_feed() 호출
        Then: briefing.llm_model == 'gemini-2.5-flash'
        """
        self._create_today_keyword()

        result = self.service.get_feed()

        assert result['briefing']['llm_model'] == 'gemini-2.5-flash'

    def test_get_feed_multiple_keywords(self):
        """
        Given: 키워드 3개
        When: get_feed() 호출
        Then: briefing.keywords 길이 3
        """
        self._create_today_keyword(keywords=[
            {'text': 'AI 반도체', 'sentiment': 'positive', 'related_symbols': ['NVDA'], 'importance': 0.9, 'reason': '이유1'},
            {'text': '금리 동결', 'sentiment': 'neutral', 'related_symbols': ['JPM'], 'importance': 0.7, 'reason': '이유2'},
            {'text': '원유 하락', 'sentiment': 'negative', 'related_symbols': ['XOM'], 'importance': 0.6, 'reason': '이유3'},
        ])

        result = self.service.get_feed()

        assert len(result['briefing']['keywords']) == 3

    def test_get_feed_keyword_with_empty_related_symbols(self):
        """
        Given: related_symbols가 빈 리스트인 키워드
        When: get_feed() 호출
        Then: news_count=0, headlines=[] 반환 (쿼리 없음)
        """
        self._create_today_keyword(keywords=[
            {
                'text': '글로벌 매크로',
                'sentiment': 'neutral',
                'related_symbols': [],
                'importance': 0.5,
                'reason': '일반 거시경제',
            }
        ])

        result = self.service.get_feed()
        kw = result['briefing']['keywords'][0]

        assert kw['news_count'] == 0
        assert kw['headlines'] == []


@pytest.mark.django_db
class TestMarketFeedServiceFallback:
    """오늘 키워드가 없고 이전 날짜 키워드로 fallback하는 경우 테스트"""

    def setup_method(self):
        self.service = MarketFeedService()

    def test_get_feed_fallback_to_previous_date(self):
        """
        Given: 오늘 키워드 없음, 어제 completed 키워드 존재
        When: get_feed() 호출
        Then: is_fallback=True, date=어제, fallback_message에 '분석 결과 표시 중' 포함
        """
        yesterday = timezone.now().date() - timedelta(days=1)
        DailyNewsKeyword.objects.create(
            date=yesterday,
            keywords=[
                {
                    'text': '금리 동결',
                    'sentiment': 'neutral',
                    'related_symbols': ['JPM'],
                    'importance': 0.8,
                    'reason': 'Fed 결정',
                }
            ],
            total_news_count=30,
            status='completed',
        )

        result = self.service.get_feed()

        assert result['is_fallback'] is True
        assert result['date'] == str(yesterday)
        assert '분석 결과 표시 중' in result['fallback_message']

    def test_get_feed_fallback_message_contains_date(self):
        """
        Given: 3일 전 completed 키워드
        When: get_feed() 호출
        Then: fallback_message에 해당 날짜 포함
        """
        three_days_ago = timezone.now().date() - timedelta(days=3)
        DailyNewsKeyword.objects.create(
            date=three_days_ago,
            keywords=[
                {
                    'text': '테스트',
                    'sentiment': 'neutral',
                    'related_symbols': [],
                    'importance': 0.5,
                    'reason': '테스트',
                }
            ],
            total_news_count=10,
            status='completed',
        )

        result = self.service.get_feed()

        assert result['is_fallback'] is True
        date_str = three_days_ago.strftime('%Y-%m-%d')
        assert date_str in result['fallback_message']

    def test_get_feed_uses_most_recent_completed_when_multiple(self):
        """
        Given: 3일 전, 2일 전 completed 키워드 2개 존재
        When: get_feed() 호출
        Then: 가장 최근 날짜(2일 전) 키워드 사용
        """
        two_days_ago = timezone.now().date() - timedelta(days=2)
        three_days_ago = timezone.now().date() - timedelta(days=3)

        DailyNewsKeyword.objects.create(
            date=three_days_ago,
            keywords=[{'text': '오래된 키워드', 'sentiment': 'neutral', 'related_symbols': [], 'importance': 0.5, 'reason': ''}],
            total_news_count=20,
            status='completed',
        )
        DailyNewsKeyword.objects.create(
            date=two_days_ago,
            keywords=[{'text': '최신 키워드', 'sentiment': 'positive', 'related_symbols': [], 'importance': 0.8, 'reason': ''}],
            total_news_count=40,
            status='completed',
        )

        result = self.service.get_feed()

        assert result['date'] == str(two_days_ago)
        assert result['briefing']['keywords'][0]['text'] == '최신 키워드'


@pytest.mark.django_db
class TestMarketFeedServiceEnrichKeywords:
    """_enrich_keywords_with_news() 메서드 테스트"""

    def setup_method(self):
        self.service = MarketFeedService()

    def test_enrich_matches_news_by_symbol(self):
        """
        Given: NVDA entity를 가진 뉴스 + NVDA related_symbols 키워드
        When: _enrich_keywords_with_news() 호출
        Then: headlines에 해당 뉴스 포함
        """
        today = timezone.now().date()

        article = NewsArticle.objects.create(
            url='https://example.com/nvda-test-news',
            title='NVIDIA Q4 실적 발표',
            summary='NVIDIA가 Q4 실적을 발표했습니다.',
            source='test',
            published_at=timezone.now(),
            category='general',
        )
        NewsEntity.objects.create(
            news=article,
            symbol='NVDA',
            entity_name='NVIDIA Corp',
            entity_type='equity',
            source='finnhub',
        )

        keywords = [
            {
                'text': 'AI 반도체',
                'sentiment': 'positive',
                'related_symbols': ['NVDA'],
                'importance': 0.9,
                'reason': '실적 발표',
            }
        ]

        result = self.service._enrich_keywords_with_news(keywords, today)

        assert len(result) == 1
        assert result[0]['news_count'] >= 1
        assert len(result[0]['headlines']) >= 1
        assert result[0]['headlines'][0]['title'] == 'NVIDIA Q4 실적 발표'
        assert result[0]['headlines'][0]['url'] == 'https://example.com/nvda-test-news'

    def test_enrich_no_news_for_symbol(self):
        """
        Given: TSLA 뉴스 없음 + TSLA related_symbols 키워드
        When: _enrich_keywords_with_news() 호출
        Then: news_count=0, headlines=[]
        """
        today = timezone.now().date()
        keywords = [
            {
                'text': '전기차',
                'sentiment': 'positive',
                'related_symbols': ['TSLA'],
                'importance': 0.7,
                'reason': '테스트',
            }
        ]

        result = self.service._enrich_keywords_with_news(keywords, today)

        assert result[0]['news_count'] == 0
        assert result[0]['headlines'] == []

    def test_enrich_headlines_limited_to_three(self):
        """
        Given: NVDA 뉴스 5개
        When: _enrich_keywords_with_news() 호출
        Then: headlines는 최대 3개까지만 반환
        """
        today = timezone.now().date()

        for i in range(5):
            article = NewsArticle.objects.create(
                url=f'https://example.com/nvda-headline-{i}',
                title=f'NVIDIA 뉴스 {i}',
                summary='테스트',
                source='test',
                published_at=timezone.now(),
                category='general',
            )
            NewsEntity.objects.create(
                news=article,
                symbol='NVDA',
                entity_name='NVIDIA Corp',
                entity_type='equity',
                source='finnhub',
            )

        keywords = [
            {
                'text': 'AI 반도체',
                'sentiment': 'positive',
                'related_symbols': ['NVDA'],
                'importance': 0.9,
                'reason': '테스트',
            }
        ]

        result = self.service._enrich_keywords_with_news(keywords, today)

        assert result[0]['news_count'] == 5    # 전체 카운트
        assert len(result[0]['headlines']) == 3  # headlines는 3개 제한

    def test_enrich_original_fields_preserved(self):
        """
        Given: 키워드에 text, sentiment, reason 등 원본 필드
        When: _enrich_keywords_with_news() 호출
        Then: 원본 필드가 그대로 유지됨
        """
        today = timezone.now().date()
        keywords = [
            {
                'text': '테스트 키워드',
                'sentiment': 'negative',
                'related_symbols': [],
                'importance': 0.3,
                'reason': '원본 이유',
            }
        ]

        result = self.service._enrich_keywords_with_news(keywords, today)

        assert result[0]['text'] == '테스트 키워드'
        assert result[0]['sentiment'] == 'negative'
        assert result[0]['importance'] == 0.3
        assert result[0]['reason'] == '원본 이유'

    def test_enrich_news_filtered_by_date(self):
        """
        Given: 오늘 뉴스 1개, 5일 전 뉴스 1개 (모두 NVDA entity)
        When: best_date=today로 _enrich_keywords_with_news() 호출
        Then: 오늘 날짜 뉴스만 포함됨
        """
        today = timezone.now().date()
        five_days_ago = timezone.now() - timedelta(days=5)

        # 오늘 뉴스
        today_article = NewsArticle.objects.create(
            url='https://example.com/nvda-today',
            title='오늘 NVIDIA 뉴스',
            summary='오늘 발표',
            source='test',
            published_at=timezone.now(),
            category='general',
        )
        NewsEntity.objects.create(
            news=today_article,
            symbol='NVDA',
            entity_name='NVIDIA Corp',
            entity_type='equity',
            source='finnhub',
        )

        # 5일 전 뉴스
        old_article = NewsArticle.objects.create(
            url='https://example.com/nvda-old',
            title='오래된 NVIDIA 뉴스',
            summary='예전 발표',
            source='test',
            published_at=five_days_ago,
            category='general',
        )
        NewsEntity.objects.create(
            news=old_article,
            symbol='NVDA',
            entity_name='NVIDIA Corp',
            entity_type='equity',
            source='finnhub',
        )

        keywords = [
            {
                'text': 'AI 반도체',
                'sentiment': 'positive',
                'related_symbols': ['NVDA'],
                'importance': 0.9,
                'reason': '테스트',
            }
        ]

        result = self.service._enrich_keywords_with_news(keywords, today)

        # 오늘 날짜 필터링 -> 오래된 뉴스 제외
        assert result[0]['news_count'] == 1
        titles = [h['title'] for h in result[0]['headlines']]
        assert '오늘 NVIDIA 뉴스' in titles
        assert '오래된 NVIDIA 뉴스' not in titles


@pytest.mark.django_db
class TestMarketFeedServiceMarketContext:
    """_get_market_context() 메서드 테스트"""

    def setup_method(self):
        self.service = MarketFeedService()

    def test_market_context_returns_dict_with_expected_keys(self):
        """
        Given: SectorPerformance/MarketMover 모델 없어도
        When: _get_market_context() 호출
        Then: top_sectors, hot_movers 키를 가진 딕셔너리 반환
        """
        result = self.service._get_market_context()

        assert 'top_sectors' in result
        assert 'hot_movers' in result

    def test_market_context_returns_lists(self):
        """
        Given: 데이터 없는 상태
        When: _get_market_context() 호출
        Then: top_sectors, hot_movers 모두 리스트 타입
        """
        result = self.service._get_market_context()

        assert isinstance(result['top_sectors'], list)
        assert isinstance(result['hot_movers'], list)

    def test_market_context_graceful_fallback_when_no_data(self):
        """
        Given: SectorPerformance, MarketMover 레코드 없음
        When: _get_market_context() 호출
        Then: 예외 없이 빈 리스트 반환
        """
        result = self.service._get_market_context()

        assert result == {'top_sectors': [], 'hot_movers': []}


@pytest.mark.django_db
class TestMarketFeedServiceCache:
    """캐시 동작 테스트"""

    def setup_method(self):
        self.service = MarketFeedService()

    def test_get_feed_result_is_cached(self):
        """
        Given: 첫 get_feed() 호출로 캐시 저장됨
        When: 두 번째 get_feed() 호출
        Then: 동일한 결과 반환 (캐시 히트)
        """
        today = timezone.now().date()
        DailyNewsKeyword.objects.create(
            date=today,
            keywords=[
                {'text': '캐시 테스트', 'sentiment': 'neutral', 'related_symbols': [], 'importance': 0.5, 'reason': '테스트'}
            ],
            total_news_count=10,
            status='completed',
            llm_model='gemini-2.5-flash',
        )

        result1 = self.service.get_feed()
        result2 = self.service.get_feed()

        assert result1 == result2

    def test_get_feed_fallback_not_cached(self):
        """
        Given: 데이터 없어 fallback 응답 반환
        When: 이후 데이터 추가 후 get_feed() 재호출
        Then: fallback 응답은 캐시되지 않으므로 새 데이터 반영
        """
        # 1차 호출: fallback
        result1 = self.service.get_feed()
        assert result1['is_fallback'] is True

        # 데이터 추가
        today = timezone.now().date()
        DailyNewsKeyword.objects.create(
            date=today,
            keywords=[
                {'text': '신규 키워드', 'sentiment': 'positive', 'related_symbols': [], 'importance': 0.8, 'reason': '신규'}
            ],
            total_news_count=20,
            status='completed',
        )

        # 2차 호출: 캐시 없으므로 새 데이터 반영
        result2 = self.service.get_feed()
        assert result2['is_fallback'] is False


# ===== InterestOptionsService 단위 테스트 =====

@pytest.mark.django_db
class TestInterestOptionsService:
    """InterestOptionsService 테스트"""

    def setup_method(self):
        self.service = InterestOptionsService()

    def test_get_options_returns_themes_and_sectors(self):
        """
        Given: SP500Constituent 없는 상태
        When: get_options() 호출
        Then: themes, sectors 키를 가진 딕셔너리 반환
        """
        result = self.service.get_options()

        assert 'themes' in result
        assert 'sectors' in result

    def test_get_options_themes_count(self):
        """
        Given: PREDEFINED_THEMES 8개 정의됨
        When: get_options() 호출
        Then: themes 8개 반환
        """
        result = self.service.get_options()

        assert len(result['themes']) == len(PREDEFINED_THEMES)
        assert len(result['themes']) == 8

    def test_get_options_theme_structure(self):
        """
        Given: 테마 목록
        When: get_options() 호출
        Then: 각 테마에 interest_type, value, display_name, sample_symbols 포함
        """
        result = self.service.get_options()
        theme = result['themes'][0]

        assert 'interest_type' in theme
        assert 'value' in theme
        assert 'display_name' in theme
        assert 'sample_symbols' in theme
        assert theme['interest_type'] == 'theme'

    def test_get_options_theme_sample_symbols_limited_to_three(self):
        """
        Given: 각 테마는 symbols 5개 정의
        When: get_options() 호출
        Then: sample_symbols는 3개까지만 포함
        """
        result = self.service.get_options()

        for theme in result['themes']:
            assert len(theme['sample_symbols']) <= 3

    def test_get_options_all_theme_values_present(self):
        """
        Given: PREDEFINED_THEMES 8개
        When: get_options() 호출
        Then: 모든 테마 value 포함
        """
        expected_values = {t['value'] for t in PREDEFINED_THEMES}
        result = self.service.get_options()
        returned_values = {t['value'] for t in result['themes']}

        assert returned_values == expected_values

    def test_get_options_sectors_empty_when_no_sp500(self):
        """
        Given: SP500Constituent 데이터 없음
        When: get_options() 호출
        Then: sectors 빈 리스트 (graceful fallback)
        """
        result = self.service.get_options()

        assert isinstance(result['sectors'], list)

    def test_get_options_sectors_with_sp500_data(self):
        """
        Given: SP500Constituent 데이터 있음
        When: get_options() 호출
        Then: sectors에 섹터 정보 포함
        """
        from stocks.models import SP500Constituent

        SP500Constituent.objects.create(
            symbol='AAPL',
            company_name='Apple Inc.',
            sector='Information Technology',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='JNJ',
            company_name='Johnson & Johnson',
            sector='Health Care',
            is_active=True,
        )

        # 캐시 무효화 후 재조회
        from django.core.cache import cache
        cache.delete(InterestOptionsService.CACHE_KEY)
        service = InterestOptionsService()
        result = service.get_options()

        sector_values = {s['value'] for s in result['sectors']}
        assert 'Information Technology' in sector_values
        assert 'Health Care' in sector_values

    def test_get_options_sector_structure(self):
        """
        Given: SP500Constituent 1개
        When: get_options() 호출
        Then: 섹터 항목에 interest_type='sector', value, display_name, sample_symbols 포함
        """
        from stocks.models import SP500Constituent
        from django.core.cache import cache

        SP500Constituent.objects.create(
            symbol='MSFT',
            company_name='Microsoft Corporation',
            sector='Information Technology',
            is_active=True,
        )

        cache.delete(InterestOptionsService.CACHE_KEY)
        service = InterestOptionsService()
        result = service.get_options()

        sector = next((s for s in result['sectors'] if s['value'] == 'Information Technology'), None)
        assert sector is not None
        assert sector['interest_type'] == 'sector'
        assert sector['display_name'] == 'Information Technology'
        assert isinstance(sector['sample_symbols'], list)

    def test_get_theme_symbols_returns_correct_list(self):
        """
        Given: 테마 value 'ai_semiconductor'
        When: get_theme_symbols() 호출
        Then: ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM'] 반환
        """
        symbols = InterestOptionsService.get_theme_symbols('ai_semiconductor')

        assert symbols == ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM']

    def test_get_theme_symbols_returns_empty_for_unknown(self):
        """
        Given: 존재하지 않는 테마 value
        When: get_theme_symbols() 호출
        Then: 빈 리스트 반환
        """
        symbols = InterestOptionsService.get_theme_symbols('nonexistent_theme')

        assert symbols == []

    def test_get_options_result_is_cached(self):
        """
        Given: 첫 get_options() 호출로 캐시 저장됨
        When: 두 번째 get_options() 호출
        Then: 동일한 결과 반환
        """
        from django.core.cache import cache
        cache.delete(InterestOptionsService.CACHE_KEY)

        service = InterestOptionsService()
        result1 = service.get_options()
        result2 = service.get_options()

        assert result1 == result2


# ===== market-feed API 엔드포인트 테스트 =====

@pytest.mark.django_db
class TestMarketFeedAPI:
    """GET /api/v1/news/market-feed/ 엔드포인트 테스트"""

    def setup_method(self):
        self.client = APIClient()

    def test_market_feed_accessible_without_auth(self):
        """
        Given: 인증 없는 클라이언트 (AllowAny)
        When: GET /api/v1/news/market-feed/
        Then: 200 OK
        """
        response = self.client.get('/api/v1/news/market-feed/')

        assert response.status_code == 200

    def test_market_feed_response_top_level_keys(self):
        """
        Given: 데이터 없는 상태에서
        When: GET /api/v1/news/market-feed/
        Then: date, is_fallback, fallback_message, briefing, market_context 포함
        """
        response = self.client.get('/api/v1/news/market-feed/')

        assert response.status_code == 200
        data = response.json()
        assert 'date' in data
        assert 'is_fallback' in data
        assert 'fallback_message' in data
        assert 'briefing' in data
        assert 'market_context' in data

    def test_market_feed_briefing_keys(self):
        """
        Given: 데이터 없는 상태에서
        When: GET /api/v1/news/market-feed/
        Then: briefing에 keywords, total_news_count, llm_model 포함
        """
        response = self.client.get('/api/v1/news/market-feed/')
        data = response.json()

        assert 'keywords' in data['briefing']
        assert 'total_news_count' in data['briefing']
        assert 'llm_model' in data['briefing']

    def test_market_feed_market_context_keys(self):
        """
        Given: 데이터 없는 상태에서
        When: GET /api/v1/news/market-feed/
        Then: market_context에 top_sectors, hot_movers 포함
        """
        response = self.client.get('/api/v1/news/market-feed/')
        data = response.json()

        assert 'top_sectors' in data['market_context']
        assert 'hot_movers' in data['market_context']

    def test_market_feed_fallback_when_no_data(self):
        """
        Given: DailyNewsKeyword 없음
        When: GET /api/v1/news/market-feed/
        Then: is_fallback=True
        """
        response = self.client.get('/api/v1/news/market-feed/')
        data = response.json()

        assert data['is_fallback'] is True

    def test_market_feed_with_today_keywords(self):
        """
        Given: 오늘 completed 키워드
        When: GET /api/v1/news/market-feed/
        Then: is_fallback=False, keywords 포함
        """
        today = timezone.now().date()
        DailyNewsKeyword.objects.create(
            date=today,
            keywords=[
                {
                    'text': '테스트 키워드',
                    'sentiment': 'neutral',
                    'related_symbols': [],
                    'importance': 0.5,
                    'reason': '테스트 이유',
                }
            ],
            total_news_count=10,
            status='completed',
            llm_model='gemini-2.5-flash',
        )

        response = self.client.get('/api/v1/news/market-feed/')
        data = response.json()

        assert response.status_code == 200
        assert data['is_fallback'] is False
        assert len(data['briefing']['keywords']) == 1

    def test_market_feed_keyword_structure_in_response(self):
        """
        Given: 오늘 completed 키워드
        When: GET /api/v1/news/market-feed/
        Then: 각 keyword에 text, sentiment, reason, news_count, headlines 포함
        """
        today = timezone.now().date()
        DailyNewsKeyword.objects.create(
            date=today,
            keywords=[
                {
                    'text': '구조 테스트',
                    'sentiment': 'positive',
                    'related_symbols': ['NVDA'],
                    'importance': 0.8,
                    'reason': '구조 확인',
                }
            ],
            total_news_count=5,
            status='completed',
            llm_model='gemini-2.5-flash',
        )

        response = self.client.get('/api/v1/news/market-feed/')
        kw = response.json()['briefing']['keywords'][0]

        assert 'text' in kw
        assert 'sentiment' in kw
        assert 'reason' in kw
        assert 'news_count' in kw
        assert 'headlines' in kw
        assert 'related_symbols' in kw


# ===== interest-options API 엔드포인트 테스트 =====

@pytest.mark.django_db
class TestInterestOptionsAPI:
    """GET /api/v1/news/interest-options/ 엔드포인트 테스트"""

    def setup_method(self):
        self.client = APIClient()
        # 캐시 초기화
        from django.core.cache import cache
        cache.delete(InterestOptionsService.CACHE_KEY)

    def test_interest_options_accessible_without_auth(self):
        """
        Given: 인증 없는 클라이언트 (AllowAny)
        When: GET /api/v1/news/interest-options/
        Then: 200 OK
        """
        response = self.client.get('/api/v1/news/interest-options/')

        assert response.status_code == 200

    def test_interest_options_response_has_themes_and_sectors(self):
        """
        Given: 정상 요청
        When: GET /api/v1/news/interest-options/
        Then: themes, sectors 키 포함
        """
        response = self.client.get('/api/v1/news/interest-options/')
        data = response.json()

        assert 'themes' in data
        assert 'sectors' in data

    def test_interest_options_themes_count(self):
        """
        Given: PREDEFINED_THEMES 8개
        When: GET /api/v1/news/interest-options/
        Then: themes 8개
        """
        response = self.client.get('/api/v1/news/interest-options/')
        data = response.json()

        assert len(data['themes']) == 8

    def test_interest_options_themes_structure(self):
        """
        Given: 정상 요청
        When: GET /api/v1/news/interest-options/
        Then: 각 테마에 interest_type, value, display_name, sample_symbols 포함
        """
        response = self.client.get('/api/v1/news/interest-options/')
        data = response.json()
        theme = data['themes'][0]

        assert 'interest_type' in theme
        assert 'value' in theme
        assert 'display_name' in theme
        assert 'sample_symbols' in theme
        assert theme['interest_type'] == 'theme'

    def test_interest_options_sectors_is_list(self):
        """
        Given: SP500 데이터 없을 때
        When: GET /api/v1/news/interest-options/
        Then: sectors는 리스트 타입 (빈 리스트 가능)
        """
        response = self.client.get('/api/v1/news/interest-options/')
        data = response.json()

        assert isinstance(data['sectors'], list)

    def test_interest_options_ai_semiconductor_theme_present(self):
        """
        Given: 정상 요청
        When: GET /api/v1/news/interest-options/
        Then: ai_semiconductor 테마 포함
        """
        response = self.client.get('/api/v1/news/interest-options/')
        data = response.json()

        values = [t['value'] for t in data['themes']]
        assert 'ai_semiconductor' in values

    def test_interest_options_with_sp500_sectors(self):
        """
        Given: SP500Constituent 데이터 2개 (다른 섹터)
        When: GET /api/v1/news/interest-options/
        Then: 해당 섹터가 sectors에 포함됨
        """
        from stocks.models import SP500Constituent

        SP500Constituent.objects.create(
            symbol='AAPL',
            company_name='Apple Inc.',
            sector='Information Technology',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='JPM',
            company_name='JPMorgan Chase',
            sector='Financials',
            is_active=True,
        )

        response = self.client.get('/api/v1/news/interest-options/')
        data = response.json()

        sector_values = [s['value'] for s in data['sectors']]
        assert 'Information Technology' in sector_values
        assert 'Financials' in sector_values


# ===== 마커 설정 =====
pytestmark = pytest.mark.django_db
