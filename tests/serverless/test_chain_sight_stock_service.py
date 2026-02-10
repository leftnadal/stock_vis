"""
Chain Sight Stock 서비스 테스트

개별 종목 페이지의 Chain Sight 기능을 검증합니다.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta

from django.utils import timezone


class TestRelationshipService:
    """RelationshipService 테스트"""

    @pytest.fixture
    def service(self):
        """서비스 인스턴스"""
        from serverless.services.relationship_service import RelationshipService
        return RelationshipService()

    @pytest.fixture
    def mock_fmp_client(self):
        """FMP 클라이언트 목"""
        with patch('serverless.services.relationship_service.FMPClient') as mock:
            client = Mock()
            mock.return_value = client
            yield client

    # ========================================
    # 시가총액 유사도 계산 테스트
    # ========================================

    def test_calculate_market_cap_similarity_same(self, service):
        """동일 시가총액 - 유사도 1.0"""
        similarity = service._calculate_market_cap_similarity(
            3000000000000,  # 3T
            3000000000000   # 3T
        )
        assert float(similarity) == pytest.approx(1.0, rel=1e-2)

    def test_calculate_market_cap_similarity_10x_diff(self, service):
        """10배 차이 - 유사도 0.5"""
        similarity = service._calculate_market_cap_similarity(
            3000000000000,   # 3T
            300000000000     # 300B (10배 차이)
        )
        # log10(3T) - log10(300B) = 12.48 - 11.48 = 1.0
        # 유사도 = 1 - 1.0/2 = 0.5
        assert float(similarity) == pytest.approx(0.5, rel=1e-1)

    def test_calculate_market_cap_similarity_100x_diff(self, service):
        """100배 차이 - 유사도 0.0"""
        similarity = service._calculate_market_cap_similarity(
            3000000000000,   # 3T
            30000000000      # 30B (100배 차이)
        )
        # log10(3T) - log10(30B) = 12.48 - 10.48 = 2.0
        # 유사도 = max(0, 1 - 2.0/2) = 0.0
        assert float(similarity) == pytest.approx(0.0, rel=1e-1)

    def test_calculate_market_cap_similarity_zero(self, service):
        """시가총액 0 - 기본값 0.5"""
        similarity = service._calculate_market_cap_similarity(0, 0)
        assert float(similarity) == 0.5

        similarity = service._calculate_market_cap_similarity(3000000000000, 0)
        assert float(similarity) == 0.5


class TestCategoryGenerator:
    """CategoryGenerator 테스트"""

    @pytest.fixture
    def generator(self):
        """생성기 인스턴스"""
        from serverless.services.category_generator import CategoryGenerator
        return CategoryGenerator()

    @pytest.fixture
    def mock_services(self):
        """서비스 목 설정"""
        with patch('serverless.services.category_generator.RelationshipService') as rel_mock, \
             patch('serverless.services.category_generator.FMPClient') as fmp_mock:

            rel_service = Mock()
            rel_mock.return_value = rel_service

            fmp_client = Mock()
            fmp_mock.return_value = fmp_client

            yield {
                'relationship_service': rel_service,
                'fmp_client': fmp_client
            }

    # ========================================
    # Tier 0 카테고리 생성 테스트
    # ========================================

    def test_build_tier0_categories_with_data(self, generator, mock_services):
        """관계 데이터가 있는 경우 - Tier 0 카테고리 생성"""
        mock_services['relationship_service'].get_relationship_counts.return_value = {
            'PEER_OF': 10,
            'SAME_INDUSTRY': 20,
            'CO_MENTIONED': 5
        }

        generator.relationship_service = mock_services['relationship_service']
        categories = generator._build_tier0_categories('NVDA')

        assert len(categories) == 3

        # 경쟁사 카테고리 확인
        peer_cat = next((c for c in categories if c['id'] == 'peer'), None)
        assert peer_cat is not None
        assert peer_cat['count'] == 10
        assert peer_cat['tier'] == 0

        # 동일 산업 카테고리 확인
        industry_cat = next((c for c in categories if c['id'] == 'same_industry'), None)
        assert industry_cat is not None
        assert industry_cat['count'] == 20

        # 뉴스 연관 카테고리 확인
        news_cat = next((c for c in categories if c['id'] == 'co_mentioned'), None)
        assert news_cat is not None
        assert news_cat['count'] == 5

    def test_build_tier0_categories_empty(self, generator, mock_services):
        """관계 데이터가 없는 경우 - 빈 카테고리"""
        mock_services['relationship_service'].get_relationship_counts.return_value = {}

        generator.relationship_service = mock_services['relationship_service']
        categories = generator._build_tier0_categories('UNKNOWN')

        assert len(categories) == 0

    # ========================================
    # AI 카테고리 테스트
    # ========================================

    def test_build_ai_categories_technology(self, generator):
        """Technology 섹터 - AI 생태계 카테고리 생성"""
        profile = {
            'sector': 'Technology',
            'industry': 'Semiconductors',
            'description': 'NVIDIA is the leading AI GPU manufacturer with CUDA platform.',
            'mktCap': 3000000000000
        }

        categories = generator._build_ai_categories('NVDA', profile, [])

        # AI 생태계 카테고리가 있어야 함
        ai_cat = next((c for c in categories if c['id'] == 'ai_ecosystem'), None)
        assert ai_cat is not None
        assert ai_cat['tier'] == 1
        assert ai_cat['is_dynamic'] is True

    def test_build_ai_categories_fintech(self, generator):
        """Fintech 관련 - 핀테크 생태계 카테고리"""
        profile = {
            'sector': 'Technology',
            'industry': 'Software',
            'description': 'Apple Pay is a major payment platform.',
            'mktCap': 3000000000000
        }

        categories = generator._build_ai_categories('AAPL', profile, [])

        # 핀테크 생태계 카테고리가 있어야 함
        fintech_cat = next((c for c in categories if c['id'] == 'fintech_ecosystem'), None)
        assert fintech_cat is not None

    def test_build_ai_categories_large_cap(self, generator):
        """대형주 - 섹터 리더 카테고리"""
        profile = {
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'description': 'Apple Inc.',
            'mktCap': 3000000000000  # 3T > 100B
        }

        categories = generator._build_ai_categories('AAPL', profile, [])

        # 섹터 리더 카테고리가 있어야 함
        leader_cat = next((c for c in categories if c['id'] == 'sector_leaders'), None)
        assert leader_cat is not None
        assert leader_cat['sector'] == 'Technology'

    def test_build_ai_categories_small_cap(self, generator):
        """소형주 - 섹터 리더 카테고리 없음"""
        profile = {
            'sector': 'Technology',
            'industry': 'Software',
            'description': 'Small tech company',
            'mktCap': 1000000000  # 1B < 100B
        }

        categories = generator._build_ai_categories('SMALL', profile, [])

        # 섹터 리더 카테고리가 없어야 함
        leader_cat = next((c for c in categories if c['id'] == 'sector_leaders'), None)
        assert leader_cat is None

    # ========================================
    # 테마 이름/설명 테스트
    # ========================================

    def test_get_theme_name(self, generator):
        """테마 ID -> 한국어 이름"""
        assert generator._get_theme_name('ai_ecosystem') == 'AI 생태계'
        assert generator._get_theme_name('ev_ecosystem') == 'EV 생태계'
        assert generator._get_theme_name('cloud_ecosystem') == '클라우드 생태계'
        assert generator._get_theme_name('unknown') == 'unknown'

    def test_get_theme_description(self, generator):
        """테마 설명 생성"""
        desc = generator._get_theme_description('ai_ecosystem', 'NVDA')
        assert 'NVDA' in desc
        assert 'AI' in desc


class TestChainSightStockService:
    """ChainSightStockService 통합 테스트"""

    @pytest.fixture
    def service(self):
        """서비스 인스턴스"""
        from serverless.services.chain_sight_stock_service import ChainSightStockService
        return ChainSightStockService()

    @pytest.fixture
    def mock_dependencies(self):
        """의존성 목 설정"""
        with patch('serverless.services.chain_sight_stock_service.CategoryGenerator') as cat_mock, \
             patch('serverless.services.chain_sight_stock_service.RelationshipService') as rel_mock, \
             patch('serverless.services.chain_sight_stock_service.FMPClient') as fmp_mock:

            cat_gen = Mock()
            cat_mock.return_value = cat_gen

            rel_service = Mock()
            rel_mock.return_value = rel_service

            fmp_client = Mock()
            fmp_mock.return_value = fmp_client

            yield {
                'category_generator': cat_gen,
                'relationship_service': rel_service,
                'fmp_client': fmp_client
            }

    # ========================================
    # AI 인사이트 생성 테스트
    # ========================================

    def test_generate_insights_with_stocks(self, service):
        """종목이 있는 경우 - 인사이트 생성"""
        category = {'id': 'peer', 'name': '경쟁사'}
        stocks = [
            {'symbol': 'AMD', 'company_name': 'AMD', 'change_percent': 2.5},
            {'symbol': 'INTC', 'company_name': 'Intel', 'change_percent': -1.0},
        ]

        insights = service._generate_insights('NVDA', category, stocks)

        assert 'NVDA' in insights
        assert '경쟁사' in insights
        assert '2개 종목' in insights

    def test_generate_insights_empty_stocks(self, service):
        """종목이 없는 경우 - 에러 메시지"""
        category = {'id': 'peer', 'name': '경쟁사'}
        stocks = []

        insights = service._generate_insights('NVDA', category, stocks)

        assert '찾을 수 없습니다' in insights

    def test_generate_insights_trend_up(self, service):
        """평균 상승 - 상승세 메시지"""
        category = {'id': 'peer', 'name': '경쟁사'}
        stocks = [
            {'symbol': 'AMD', 'company_name': 'AMD', 'change_percent': 3.0},
            {'symbol': 'INTC', 'company_name': 'Intel', 'change_percent': 2.0},
        ]

        insights = service._generate_insights('NVDA', category, stocks)
        assert '상승' in insights

    def test_generate_insights_trend_down(self, service):
        """평균 하락 - 하락세 메시지"""
        category = {'id': 'peer', 'name': '경쟁사'}
        stocks = [
            {'symbol': 'AMD', 'company_name': 'AMD', 'change_percent': -3.0},
            {'symbol': 'INTC', 'company_name': 'Intel', 'change_percent': -2.0},
        ]

        insights = service._generate_insights('NVDA', category, stocks)
        assert '하락' in insights

    # ========================================
    # 후속 질문 생성 테스트
    # ========================================

    def test_generate_follow_up_questions_peer(self, service):
        """경쟁사 카테고리 - 후속 질문"""
        category = {'id': 'peer', 'name': '경쟁사'}
        questions = service._generate_follow_up_questions('NVDA', category)

        assert len(questions) <= 2
        assert any('경쟁사' in q or '밸류에이션' in q or '시장 점유율' in q for q in questions)

    def test_generate_follow_up_questions_industry(self, service):
        """동일 산업 카테고리 - 후속 질문"""
        category = {'id': 'same_industry', 'name': '동일 산업'}
        questions = service._generate_follow_up_questions('NVDA', category)

        assert len(questions) <= 2
        assert any('산업' in q for q in questions)

    def test_generate_follow_up_questions_news(self, service):
        """뉴스 연관 카테고리 - 후속 질문"""
        category = {'id': 'co_mentioned', 'name': '뉴스 연관'}
        questions = service._generate_follow_up_questions('NVDA', category)

        assert len(questions) <= 2
        assert any('뉴스' in q or '감성' in q or '이슈' in q for q in questions)


# ========================================
# Django DB 테스트
# ========================================

@pytest.mark.django_db
class TestStockRelationshipModel:
    """StockRelationship 모델 테스트"""

    def test_create_relationship(self):
        """관계 생성"""
        from serverless.models import StockRelationship

        rel = StockRelationship.objects.create(
            source_symbol='NVDA',
            target_symbol='AMD',
            relationship_type='PEER_OF',
            strength=Decimal('0.85'),
            source_provider='fmp',
            context={'source': 'test'}
        )

        assert rel.id is not None
        assert str(rel) == 'NVDA --PEER_OF--> AMD'

    def test_unique_constraint(self):
        """중복 관계 방지"""
        from serverless.models import StockRelationship
        from django.db import IntegrityError

        StockRelationship.objects.create(
            source_symbol='NVDA',
            target_symbol='AMD',
            relationship_type='PEER_OF'
        )

        with pytest.raises(IntegrityError):
            StockRelationship.objects.create(
                source_symbol='NVDA',
                target_symbol='AMD',
                relationship_type='PEER_OF'
            )

    def test_different_relationship_types_allowed(self):
        """다른 관계 타입은 허용"""
        from serverless.models import StockRelationship

        StockRelationship.objects.create(
            source_symbol='NVDA',
            target_symbol='TSM',
            relationship_type='PEER_OF'
        )

        # 다른 관계 타입은 허용
        rel2 = StockRelationship.objects.create(
            source_symbol='NVDA',
            target_symbol='TSM',
            relationship_type='SAME_INDUSTRY'
        )

        assert rel2.id is not None


@pytest.mark.django_db
class TestCategoryCacheModel:
    """CategoryCache 모델 테스트"""

    def test_create_cache(self):
        """캐시 생성"""
        from serverless.models import CategoryCache

        cache = CategoryCache.objects.create(
            symbol='NVDA',
            date=date.today(),
            categories=[
                {'id': 'peer', 'name': '경쟁사', 'tier': 0, 'count': 10}
            ],
            generation_time_ms=100
        )

        assert cache.id is not None
        assert cache.expires_at is not None
        # 24시간 후 만료
        assert cache.expires_at > timezone.now()

    def test_auto_expires_at(self):
        """expires_at 자동 설정"""
        from serverless.models import CategoryCache

        cache = CategoryCache(
            symbol='AAPL',
            date=date.today(),
            categories=[]
        )
        cache.save()

        # 24시간 후 만료
        expected_expiry = timezone.now() + timedelta(hours=24)
        assert abs((cache.expires_at - expected_expiry).total_seconds()) < 60
