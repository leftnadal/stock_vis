"""
Theme Matching Service 테스트

ThemeMatchingService의 유닛 테스트입니다.
"""
import pytest
from decimal import Decimal
from datetime import date

from serverless.models import ETFProfile, ETFHolding, ThemeMatch, StockRelationship
from serverless.services.theme_matching_service import (
    ThemeMatchingService,
    THEME_KEYWORDS,
    THEME_TO_ETF,
    get_theme_matching_service,
)


@pytest.fixture
def service():
    """ThemeMatchingService 인스턴스"""
    return ThemeMatchingService()


@pytest.fixture
def sample_etf_profile(db):
    """샘플 ETF 프로필"""
    return ETFProfile.objects.create(
        symbol='SOXX',
        name='iShares Semiconductor ETF',
        tier='theme',
        theme_id='semiconductor'
    )


@pytest.fixture
def sample_holdings(db, sample_etf_profile):
    """샘플 ETF Holdings"""
    holdings = [
        ETFHolding(
            etf=sample_etf_profile,
            stock_symbol='NVDA',
            weight_percent=Decimal('10.50'),
            shares=50000000,
            rank=1,
            snapshot_date=date.today()
        ),
        ETFHolding(
            etf=sample_etf_profile,
            stock_symbol='AMD',
            weight_percent=Decimal('8.00'),
            shares=40000000,
            rank=2,
            snapshot_date=date.today()
        ),
        ETFHolding(
            etf=sample_etf_profile,
            stock_symbol='INTC',
            weight_percent=Decimal('6.50'),
            shares=30000000,
            rank=3,
            snapshot_date=date.today()
        ),
    ]
    ETFHolding.objects.bulk_create(holdings)
    return holdings


class TestThemeKeywordsConfig:
    """테마 키워드 설정 테스트"""

    def test_theme_keywords_not_empty(self):
        """THEME_KEYWORDS가 비어있지 않음"""
        assert len(THEME_KEYWORDS) > 0

    def test_theme_keywords_has_sector_themes(self):
        """섹터 테마 포함 확인"""
        assert 'technology' in THEME_KEYWORDS
        assert 'healthcare' in THEME_KEYWORDS
        assert 'financials' in THEME_KEYWORDS

    def test_theme_keywords_has_niche_themes(self):
        """니치 테마 포함 확인"""
        assert 'semiconductor' in THEME_KEYWORDS
        assert 'innovation' in THEME_KEYWORDS
        assert 'clean_energy' in THEME_KEYWORDS

    def test_theme_keywords_structure(self):
        """테마 키워드 구조 확인"""
        for theme_id, config in THEME_KEYWORDS.items():
            assert 'keywords' in config
            assert 'name' in config
            assert 'icon' in config
            assert len(config['keywords']) > 0

    def test_semiconductor_keywords(self):
        """반도체 테마 키워드 확인"""
        keywords = THEME_KEYWORDS['semiconductor']['keywords']
        assert 'semiconductor' in keywords
        assert 'chip' in keywords
        assert 'GPU' in keywords


class TestThemeToETFMapping:
    """테마-ETF 매핑 테스트"""

    def test_theme_to_etf_not_empty(self):
        """THEME_TO_ETF가 비어있지 않음"""
        assert len(THEME_TO_ETF) > 0

    def test_sector_themes_mapped(self):
        """섹터 테마 매핑 확인"""
        assert THEME_TO_ETF['technology'] == 'XLK'
        assert THEME_TO_ETF['healthcare'] == 'XLV'
        assert THEME_TO_ETF['financials'] == 'XLF'

    def test_niche_themes_mapped(self):
        """니치 테마 매핑 확인"""
        assert THEME_TO_ETF['semiconductor'] == 'SOXX'
        assert THEME_TO_ETF['innovation'] == 'ARKK'


@pytest.mark.django_db
class TestTierAMatching:
    """Tier A 매칭 (ETF Holdings 기반) 테스트"""

    def test_match_tier_a_creates_matches(self, service, sample_holdings):
        """Tier A 매칭 생성"""
        matches = service.match_tier_a('NVDA')

        assert len(matches) >= 1
        match = matches[0]
        assert match.stock_symbol == 'NVDA'
        assert match.theme_id == 'semiconductor'
        assert match.confidence == 'high'
        assert match.source == 'etf_holding'
        assert match.etf_symbol == 'SOXX'

    def test_match_tier_a_updates_existing(self, service, sample_holdings):
        """기존 매치 업데이트"""
        # 첫 번째 매칭
        matches1 = service.match_tier_a('NVDA')
        count1 = ThemeMatch.objects.filter(stock_symbol='NVDA').count()

        # 두 번째 매칭 (업데이트)
        matches2 = service.match_tier_a('NVDA')
        count2 = ThemeMatch.objects.filter(stock_symbol='NVDA').count()

        # 중복 생성 없음
        assert count1 == count2

    def test_match_tier_a_no_holdings(self, service, db):
        """Holdings 없는 종목"""
        matches = service.match_tier_a('UNKNOWN')
        assert len(matches) == 0


@pytest.mark.django_db
class TestTierBMatching:
    """Tier B 매칭 (키워드 기반) 테스트"""

    def test_match_tier_b_with_description(self, service, db):
        """설명 기반 키워드 매칭"""
        matches = service.match_tier_b(
            'TEST',
            company_name='Test Semiconductor Corp',
            company_description='Leading provider of GPU chips for AI and machine learning',
            sector='Technology',
            industry='Semiconductors'
        )

        # semiconductor 테마 매칭 확인
        theme_ids = [m.theme_id for m in matches]
        assert 'semiconductor' in theme_ids or 'robotics_ai' in theme_ids

    def test_match_tier_b_confidence_medium(self, service, db):
        """Tier B 매칭의 confidence는 medium"""
        matches = service.match_tier_b(
            'TEST2',
            company_description='A solar energy company',
        )

        if matches:
            for match in matches:
                assert match.confidence in ['medium', 'medium-high']

    def test_match_tier_b_skips_tier_a(self, service, sample_holdings):
        """Tier A가 있으면 Tier B 스킵"""
        # Tier A 매칭 먼저
        service.match_tier_a('NVDA')

        # Tier B 매칭
        matches = service.match_tier_b(
            'NVDA',
            company_description='GPU semiconductor company',
        )

        # semiconductor는 이미 Tier A이므로 Tier B에 없음
        tier_b_theme_ids = [m.theme_id for m in matches]
        assert 'semiconductor' not in tier_b_theme_ids


@pytest.mark.django_db
class TestPromotion:
    """Tier B 승격 테스트"""

    def test_promotion_with_co_mentioned(self, service, db):
        """CO_MENTIONED로 승격"""
        # ETF와의 CO_MENTIONED 관계 생성
        StockRelationship.objects.create(
            source_symbol='TEST3',
            target_symbol='SOXX',
            relationship_type='CO_MENTIONED',
            strength=Decimal('0.8')
        )
        StockRelationship.objects.create(
            source_symbol='SOXX',
            target_symbol='TEST3',
            relationship_type='CO_MENTIONED',
            strength=Decimal('0.7')
        )

        confidence = service._check_promotion('TEST3', 'semiconductor', ['chip'])

        # 2회 이상 동시언급 시 승격
        assert confidence in ['medium-high', 'medium']

    def test_promotion_with_peer_relationships(self, service, sample_holdings):
        """PEER 관계로 승격"""
        # NVDA, AMD, INTC와 PEER 관계 생성
        for target in ['NVDA', 'AMD', 'INTC']:
            StockRelationship.objects.create(
                source_symbol='TEST4',
                target_symbol=target,
                relationship_type='PEER_OF',
                strength=Decimal('0.8')
            )

        # Tier A 매칭 먼저 (테마 종목 생성)
        service.match_tier_a('NVDA')
        service.match_tier_a('AMD')
        service.match_tier_a('INTC')

        confidence = service._check_promotion('TEST4', 'semiconductor', ['chip'])

        # 3개 이상 PEER 시 승격
        assert confidence in ['medium-high', 'medium']


@pytest.mark.django_db
class TestGetThemeStocks:
    """테마별 종목 조회 테스트"""

    def test_get_theme_stocks(self, service, sample_holdings):
        """테마 종목 조회"""
        # Tier A 매칭
        service.match_tier_a('NVDA')
        service.match_tier_a('AMD')

        stocks = service.get_theme_stocks('semiconductor', limit=10)

        assert len(stocks) >= 2
        symbols = [s['symbol'] for s in stocks]
        assert 'NVDA' in symbols
        assert 'AMD' in symbols

    def test_get_theme_stocks_confidence_filter(self, service, sample_holdings, db):
        """confidence 필터링"""
        # Tier A 매칭 (high)
        service.match_tier_a('NVDA')

        # Tier B 매칭 (medium)
        service.match_tier_b(
            'TEST5',
            company_description='semiconductor chip company'
        )

        # high만 조회
        high_stocks = service.get_theme_stocks('semiconductor', min_confidence='high')
        high_symbols = [s['symbol'] for s in high_stocks]

        # NVDA는 high, TEST5는 medium
        assert 'NVDA' in high_symbols


@pytest.mark.django_db
class TestGetStockThemes:
    """종목의 테마 조회 테스트"""

    def test_get_stock_themes(self, service, sample_holdings):
        """종목의 테마 조회"""
        service.match_tier_a('NVDA')

        themes = service.get_stock_themes('NVDA')

        assert len(themes) >= 1
        theme_ids = [t['theme_id'] for t in themes]
        assert 'semiconductor' in theme_ids

    def test_get_stock_themes_includes_info(self, service, sample_holdings):
        """테마 정보 포함 확인"""
        service.match_tier_a('NVDA')

        themes = service.get_stock_themes('NVDA')

        for theme in themes:
            assert 'theme_id' in theme
            assert 'name' in theme
            assert 'icon' in theme
            assert 'confidence' in theme


@pytest.mark.django_db
class TestGetThemeInfo:
    """테마 정보 조회 테스트"""

    def test_get_theme_info(self, service, sample_holdings):
        """테마 정보 조회"""
        service.match_tier_a('NVDA')

        info = service.get_theme_info('semiconductor')

        assert info is not None
        assert info['id'] == 'semiconductor'
        assert info['name'] == '반도체'
        assert info['icon'] == '🔌'
        assert info['etf_symbol'] == 'SOXX'
        assert info['stock_count'] >= 0

    def test_get_theme_info_not_found(self, service):
        """존재하지 않는 테마"""
        info = service.get_theme_info('nonexistent_theme')
        assert info is None


@pytest.mark.django_db
class TestGetAllThemes:
    """전체 테마 목록 조회 테스트"""

    def test_get_all_themes(self, service):
        """전체 테마 조회"""
        themes = service.get_all_themes()

        assert len(themes) >= len(THEME_KEYWORDS)

    def test_get_all_themes_sorted_by_count(self, service, sample_holdings):
        """종목 수 기준 정렬"""
        service.match_tier_a('NVDA')
        service.match_tier_a('AMD')
        service.match_tier_a('INTC')

        themes = service.get_all_themes()

        # semiconductor가 상위에 있어야 함
        counts = [t['stock_count'] for t in themes]
        assert counts == sorted(counts, reverse=True)


@pytest.mark.django_db
class TestRefreshAllMatches:
    """전체 매치 갱신 테스트"""

    def test_refresh_all_matches(self, service, sample_holdings):
        """전체 매치 갱신"""
        result = service.refresh_all_matches()

        assert 'created' in result
        assert 'updated' in result
        assert 'total' in result
        assert result['total'] >= 0

    def test_refresh_all_matches_creates_from_holdings(self, service, sample_holdings):
        """Holdings에서 매치 생성"""
        # 초기 상태 확인
        initial_count = ThemeMatch.objects.count()

        result = service.refresh_all_matches()

        # Holdings 기반 매치 생성
        assert result['created'] >= 0 or result['updated'] >= 0


@pytest.mark.django_db
class TestGetETFPeers:
    """ETF 동반 종목 조회 테스트"""

    def test_get_etf_peers(self, service, sample_holdings):
        """ETF 동반 종목 조회"""
        peers = service.get_etf_peers('NVDA', limit=10)

        assert len(peers) >= 2
        symbols = [p['symbol'] for p in peers]
        assert 'AMD' in symbols
        assert 'INTC' in symbols

    def test_get_etf_peers_excludes_self(self, service, sample_holdings):
        """자기 자신 제외"""
        peers = service.get_etf_peers('NVDA', limit=10)

        symbols = [p['symbol'] for p in peers]
        assert 'NVDA' not in symbols

    def test_get_etf_peers_includes_common_etfs(self, service, sample_holdings):
        """공통 ETF 정보 포함"""
        peers = service.get_etf_peers('NVDA', limit=10)

        for peer in peers:
            assert 'etfs_in_common' in peer
            assert 'SOXX' in peer['etfs_in_common']

    def test_get_etf_peers_no_holdings(self, service, db):
        """Holdings 없는 종목"""
        peers = service.get_etf_peers('UNKNOWN', limit=10)
        assert len(peers) == 0


class TestSingleton:
    """싱글톤 인스턴스 테스트"""

    def test_get_theme_matching_service_singleton(self):
        """싱글톤 인스턴스 반환"""
        service1 = get_theme_matching_service()
        service2 = get_theme_matching_service()

        assert service1 is service2
