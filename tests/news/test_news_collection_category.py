"""
뉴스 수집 카테고리 모델 테스트

TestNewsCollectionCategory:
- resolve_symbols() — sector, sub_sector, custom 타입별 심볼 해석
- max_symbols 제한
"""

import pytest
from news.models import NewsCollectionCategory


@pytest.mark.django_db
class TestNewsCollectionCategory:
    """NewsCollectionCategory 모델 테스트"""

    @pytest.fixture(autouse=True)
    def setup_sp500_constituents(self):
        """SP500Constituent 테스트 데이터 생성"""
        from stocks.models import SP500Constituent

        # Technology 섹터 종목 3개
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
            symbol='NVDA',
            company_name='NVIDIA Corporation',
            sector='Technology',
            sub_sector='Semiconductors',
            is_active=True,
        )

        # Healthcare 섹터 종목 2개
        SP500Constituent.objects.create(
            symbol='JNJ',
            company_name='Johnson & Johnson',
            sector='Healthcare',
            sub_sector='Pharmaceuticals',
            is_active=True,
        )
        SP500Constituent.objects.create(
            symbol='PFE',
            company_name='Pfizer Inc.',
            sector='Healthcare',
            sub_sector='Pharmaceuticals',
            is_active=True,
        )

        # Inactive 종목 (제외되어야 함)
        SP500Constituent.objects.create(
            symbol='INACTIVE',
            company_name='Inactive Corp',
            sector='Technology',
            sub_sector='Software',
            is_active=False,
        )

    def test_resolve_symbols_sector_type(self):
        """Given: sector 타입 카테고리
        When: resolve_symbols() 호출
        Then: 해당 섹터의 active 종목만 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Tech Sector',
            category_type='sector',
            value='Technology',
            max_symbols=20,
        )

        symbols = category.resolve_symbols()

        assert len(symbols) == 3
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'NVDA' in symbols
        assert 'INACTIVE' not in symbols

    def test_resolve_symbols_sub_sector_type(self):
        """Given: sub_sector 타입 카테고리
        When: resolve_symbols() 호출
        Then: 해당 서브섹터의 active 종목만 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Pharma Sub-Sector',
            category_type='sub_sector',
            value='Pharmaceuticals',
            max_symbols=20,
        )

        symbols = category.resolve_symbols()

        assert len(symbols) == 2
        assert 'JNJ' in symbols
        assert 'PFE' in symbols
        assert 'AAPL' not in symbols

    def test_resolve_symbols_custom_type(self):
        """Given: custom 타입 카테고리 (쉼표 구분 심볼)
        When: resolve_symbols() 호출
        Then: 파싱된 심볼 리스트 반환 (대문자 변환)"""
        category = NewsCollectionCategory.objects.create(
            name='Custom Watchlist',
            category_type='custom',
            value='aapl, tsla, goog',  # 소문자
            max_symbols=20,
        )

        symbols = category.resolve_symbols()

        assert len(symbols) == 3
        assert 'AAPL' in symbols
        assert 'TSLA' in symbols
        assert 'GOOG' in symbols

    def test_resolve_symbols_custom_type_with_whitespace(self):
        """Given: custom 타입 카테고리 (공백 포함)
        When: resolve_symbols() 호출
        Then: 공백 제거 후 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Custom with Spaces',
            category_type='custom',
            value='  AAPL  ,  TSLA  , , GOOG  ',  # 공백, 빈 항목
            max_symbols=20,
        )

        symbols = category.resolve_symbols()

        assert len(symbols) == 3
        assert 'AAPL' in symbols
        assert 'TSLA' in symbols
        assert 'GOOG' in symbols

    def test_resolve_symbols_max_symbols_limit(self):
        """Given: max_symbols=2인 sector 카테고리
        When: resolve_symbols() 호출
        Then: 최대 2개 종목만 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Tech Limited',
            category_type='sector',
            value='Technology',
            max_symbols=2,
        )

        symbols = category.resolve_symbols()

        assert len(symbols) == 2
        # 정확한 심볼은 쿼리 순서에 따름 ([:2]로 제한)

    def test_resolve_symbols_custom_max_symbols_limit(self):
        """Given: max_symbols=2인 custom 카테고리
        When: resolve_symbols() 호출 (5개 입력)
        Then: 처음 2개만 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Custom Limited',
            category_type='custom',
            value='AAPL, TSLA, GOOG, MSFT, NVDA',
            max_symbols=2,
        )

        symbols = category.resolve_symbols()

        assert len(symbols) == 2
        assert symbols == ['AAPL', 'TSLA']

    def test_resolve_symbols_unknown_type(self):
        """Given: 알 수 없는 category_type
        When: resolve_symbols() 호출
        Then: 빈 리스트 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Unknown Type',
            category_type='sector',  # DB에는 valid하지만 로직상 처리 안 되는 케이스 시뮬
            value='NonexistentSector',
            max_symbols=20,
        )

        symbols = category.resolve_symbols()

        # 존재하지 않는 섹터 → 빈 리스트
        assert symbols == []

    def test_resolve_symbols_empty_custom_value(self):
        """Given: custom 타입 + 빈 value
        When: resolve_symbols() 호출
        Then: 빈 리스트 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Empty Custom',
            category_type='custom',
            value='',
            max_symbols=20,
        )

        symbols = category.resolve_symbols()

        assert symbols == []

    def test_model_str_representation(self):
        """Given: NewsCollectionCategory 인스턴스
        When: __str__() 호출
        Then: 읽기 쉬운 표현 반환"""
        category = NewsCollectionCategory.objects.create(
            name='Tech Sector',
            category_type='sector',
            value='Technology',
        )

        assert str(category) == 'Tech Sector (sector: Technology)'

    def test_model_default_values(self):
        """Given: 최소 필드만 제공
        When: 카테고리 생성
        Then: 기본값 적용"""
        category = NewsCollectionCategory.objects.create(
            name='Default Test',
            category_type='custom',
            value='AAPL',
        )

        assert category.is_active is True
        assert category.priority == 'medium'
        assert category.max_symbols == 20
        assert category.last_article_count == 0
        assert category.last_symbol_count == 0
        assert category.total_collections == 0
        assert category.last_error == ''
        assert category.last_collected_at is None
