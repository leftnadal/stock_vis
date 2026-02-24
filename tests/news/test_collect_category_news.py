"""
뉴스 수집 카테고리 태스크 테스트

TestCollectCategoryNews:
- collect_category_news(category_id) — 특정 카테고리 수집
- collect_category_news(priority_filter) — 우선순위 필터
- 카테고리 간 심볼 dedup
- 수집 후 통계 업데이트
"""

import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from news.tasks import collect_category_news
from news.models import NewsCollectionCategory


@pytest.mark.django_db
class TestCollectCategoryNews:
    """collect_category_news 태스크 테스트"""

    @pytest.fixture(autouse=True)
    def setup_sp500_constituents(self):
        """SP500Constituent 테스트 데이터 생성"""
        from stocks.models import SP500Constituent

        SP500Constituent.objects.create(
            symbol='AAPL',
            company_name='Apple Inc.',
            sector='Technology',
            sub_sector='Consumer Electronics',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='MSFT',
            company_name='Microsoft Corporation',
            sector='Technology',
            sub_sector='Software',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='JNJ',
            company_name='Johnson & Johnson',
            sector='Healthcare',
            sub_sector='Pharmaceuticals',
            is_active=True,
        )

    @pytest.fixture
    def mock_aggregator(self):
        """NewsAggregatorService.fetch_and_save_company_news mock"""
        with patch('news.services.aggregator.NewsAggregatorService') as mock_service:
            # aggregator.fetch_and_save_company_news 반환값
            mock_instance = MagicMock()
            mock_instance.fetch_and_save_company_news.return_value = {
                'saved': 5,
                'updated': 2,
            }
            mock_service.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_sleep(self):
        """time.sleep mock (테스트 속도 향상)"""
        with patch('news.tasks.time.sleep') as mock:
            yield mock

    def test_collect_category_news_by_id(self, mock_aggregator, mock_sleep):
        """Given: category_id=1인 카테고리
        When: collect_category_news(category_id=1) 실행
        Then: 해당 카테고리의 심볼로 뉴스 수집 + 통계 업데이트"""
        category = NewsCollectionCategory.objects.create(
            name='Tech Sector',
            category_type='sector',
            value='Technology',
            is_active=True,
            priority='high',
            max_symbols=20,
        )

        result = collect_category_news(category_id=category.id)

        # 심볼 2개 (AAPL, MSFT)
        assert result['categories_processed'] == 1
        assert result['total_symbols'] == 2
        assert result['total_saved'] == 10  # 5 * 2
        assert result['total_updated'] == 4  # 2 * 2
        assert result['errors'] == 0

        # fetch_and_save_company_news 호출 검증
        assert mock_aggregator.fetch_and_save_company_news.call_count == 2
        mock_aggregator.fetch_and_save_company_news.assert_any_call(
            symbol='AAPL',
            days=1,
            use_marketaux=False,
        )
        mock_aggregator.fetch_and_save_company_news.assert_any_call(
            symbol='MSFT',
            days=1,
            use_marketaux=False,
        )

        # time.sleep 호출 검증 (rate limit)
        assert mock_sleep.call_count == 2

        # 카테고리 통계 업데이트 검증
        category.refresh_from_db()
        assert category.last_collected_at is not None
        assert category.last_article_count == 10
        assert category.last_symbol_count == 2
        assert category.total_collections == 1
        assert category.last_error == ''

    def test_collect_category_news_priority_filter(self, mock_aggregator, mock_sleep):
        """Given: 우선순위가 'high'인 카테고리 2개
        When: collect_category_news(priority_filter='high') 실행
        Then: high 우선순위 카테고리만 수집"""
        # High priority 카테고리
        cat1 = NewsCollectionCategory.objects.create(
            name='Tech High',
            category_type='custom',
            value='AAPL',
            is_active=True,
            priority='high',
        )
        cat2 = NewsCollectionCategory.objects.create(
            name='Healthcare High',
            category_type='custom',
            value='JNJ',
            is_active=True,
            priority='high',
        )

        # Medium priority 카테고리 (제외되어야 함)
        NewsCollectionCategory.objects.create(
            name='Tech Medium',
            category_type='custom',
            value='MSFT',
            is_active=True,
            priority='medium',
        )

        result = collect_category_news(priority_filter='high')

        assert result['categories_processed'] == 2
        assert result['total_symbols'] == 2  # AAPL, JNJ (dedup)
        assert result['total_saved'] == 10  # 5 * 2
        assert mock_aggregator.fetch_and_save_company_news.call_count == 2

    def test_collect_category_news_symbol_dedup(self, mock_aggregator, mock_sleep):
        """Given: 같은 심볼을 포함하는 카테고리 2개
        When: collect_category_news() 실행
        Then: 심볼별 1회만 수집"""
        NewsCollectionCategory.objects.create(
            name='Custom 1',
            category_type='custom',
            value='AAPL, MSFT',
            is_active=True,
        )
        NewsCollectionCategory.objects.create(
            name='Custom 2',
            category_type='custom',
            value='MSFT, JNJ',  # MSFT 중복
            is_active=True,
        )

        result = collect_category_news()

        # 중복 제거 → AAPL, MSFT, JNJ (3개)
        assert result['total_symbols'] == 3
        assert result['total_saved'] == 15  # 5 * 3
        assert mock_aggregator.fetch_and_save_company_news.call_count == 3

        # MSFT는 1번만 호출되어야 함
        calls = mock_aggregator.fetch_and_save_company_news.call_args_list
        msft_calls = [c for c in calls if c[1]['symbol'] == 'MSFT']
        assert len(msft_calls) == 1

    def test_collect_category_news_no_categories(self, mock_aggregator, mock_sleep):
        """Given: 활성 카테고리가 없음
        When: collect_category_news() 실행
        Then: 빈 결과 반환"""
        result = collect_category_news()

        assert result['categories_processed'] == 0
        assert result['total_symbols'] == 0
        assert result['total_saved'] == 0
        assert result['total_updated'] == 0
        assert result['errors'] == 0
        assert mock_aggregator.fetch_and_save_company_news.call_count == 0

    def test_collect_category_news_inactive_category_excluded(self, mock_aggregator, mock_sleep):
        """Given: is_active=False인 카테고리
        When: collect_category_news() 실행
        Then: 해당 카테고리는 무시"""
        NewsCollectionCategory.objects.create(
            name='Active Category',
            category_type='custom',
            value='AAPL',
            is_active=True,
        )
        NewsCollectionCategory.objects.create(
            name='Inactive Category',
            category_type='custom',
            value='MSFT',
            is_active=False,  # 비활성
        )

        result = collect_category_news()

        assert result['categories_processed'] == 1
        assert result['total_symbols'] == 1  # AAPL만
        assert mock_aggregator.fetch_and_save_company_news.call_count == 1

    def test_collect_category_news_handles_fetch_error(self, mock_aggregator, mock_sleep):
        """Given: 특정 심볼 수집 시 에러 발생
        When: collect_category_news() 실행
        Then: 에러 카운트 증가, 다른 심볼은 계속 처리"""
        # AAPL은 성공, MSFT는 실패
        def side_effect(symbol, **kwargs):
            if symbol == 'MSFT':
                raise Exception('API Error')
            return {'saved': 5, 'updated': 2}

        mock_aggregator.fetch_and_save_company_news.side_effect = side_effect

        NewsCollectionCategory.objects.create(
            name='Tech',
            category_type='custom',
            value='AAPL, MSFT',
            is_active=True,
        )

        result = collect_category_news()

        assert result['total_symbols'] == 2
        assert result['total_saved'] == 5  # AAPL만 성공
        assert result['errors'] == 1
        assert mock_aggregator.fetch_and_save_company_news.call_count == 2

    def test_collect_category_news_updates_stats_per_category(self, mock_aggregator, mock_sleep):
        """Given: 카테고리 2개
        When: collect_category_news() 실행
        Then: 각 카테고리별 통계 업데이트"""
        cat1 = NewsCollectionCategory.objects.create(
            name='Cat1',
            category_type='custom',
            value='AAPL',
            is_active=True,
        )
        cat2 = NewsCollectionCategory.objects.create(
            name='Cat2',
            category_type='custom',
            value='MSFT, JNJ',
            is_active=True,
        )

        result = collect_category_news()

        # Cat1: AAPL 1개 → saved=5
        cat1.refresh_from_db()
        assert cat1.last_article_count == 5
        assert cat1.last_symbol_count == 1
        assert cat1.total_collections == 1

        # Cat2: MSFT, JNJ 2개 → saved=10
        cat2.refresh_from_db()
        assert cat2.last_article_count == 10
        assert cat2.last_symbol_count == 2
        assert cat2.total_collections == 1

    def test_collect_category_news_returns_per_category_detail(self, mock_aggregator, mock_sleep):
        """Given: 카테고리 2개
        When: collect_category_news() 실행
        Then: per_category 딕셔너리에 상세 결과 포함"""
        NewsCollectionCategory.objects.create(
            name='Cat1',
            category_type='custom',
            value='AAPL',
            is_active=True,
        )
        NewsCollectionCategory.objects.create(
            name='Cat2',
            category_type='custom',
            value='MSFT',
            is_active=True,
        )

        result = collect_category_news()

        assert 'per_category' in result
        assert 'Cat1' in result['per_category']
        assert 'Cat2' in result['per_category']

        assert result['per_category']['Cat1'] == {'symbols': 1, 'saved': 5}
        assert result['per_category']['Cat2'] == {'symbols': 1, 'saved': 5}

    def test_collect_category_news_nonexistent_category_id(self, mock_aggregator, mock_sleep):
        """Given: 존재하지 않는 category_id
        When: collect_category_news(category_id=999) 실행
        Then: 빈 결과 반환 (에러 아님)"""
        result = collect_category_news(category_id=999)

        assert result['categories_processed'] == 0
        assert result['total_symbols'] == 0
        assert mock_aggregator.fetch_and_save_company_news.call_count == 0

    def test_collect_category_news_rate_limit_sleep(self, mock_aggregator, mock_sleep):
        """Given: 심볼 3개
        When: collect_category_news() 실행
        Then: 각 심볼 후 2초 sleep (Finnhub rate limit)"""
        NewsCollectionCategory.objects.create(
            name='Multi Symbol',
            category_type='custom',
            value='AAPL, MSFT, JNJ',
            is_active=True,
        )

        collect_category_news()

        # 3개 심볼 → sleep 3번
        assert mock_sleep.call_count == 3
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 2  # time.sleep(2)
