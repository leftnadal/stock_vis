"""
Chain Sight DNA 서비스 테스트

연관 종목 발견 시스템의 로직을 검증합니다.
"""
import pytest
from decimal import Decimal
from serverless.services.chain_sight_service import ChainSightService


class TestChainSightService:
    """Chain Sight DNA 서비스 테스트"""

    @pytest.fixture
    def service(self):
        """서비스 인스턴스"""
        return ChainSightService()

    @pytest.fixture
    def sample_stocks(self):
        """테스트용 샘플 종목 데이터"""
        return [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "marketCap": 3000000000000,
                "pe": 25.5,
                "roe": 150.0,
                "grossProfitMargin": 38.0
            },
            {
                "symbol": "MSFT",
                "companyName": "Microsoft Corporation",
                "sector": "Technology",
                "industry": "Software",
                "marketCap": 2500000000000,
                "pe": 28.0,
                "roe": 45.0,
                "grossProfitMargin": 68.0
            }
        ]

    # ========================================
    # 평균 메트릭 계산 테스트
    # ========================================

    def test_calculate_average_metrics(self, service, sample_stocks):
        """평균 메트릭 계산"""
        avg = service._calculate_average_metrics(sample_stocks)

        assert 'market_cap' in avg
        assert 'pe' in avg
        assert 'roe' in avg
        assert 'profit_margin' in avg

        # 시가총액 평균: (3T + 2.5T) / 2 = 2.75T
        assert avg['market_cap'] == pytest.approx(2750000000000, rel=1e-5)

        # PER 평균: (25.5 + 28.0) / 2 = 26.75
        assert avg['pe'] == pytest.approx(26.75, rel=1e-2)

        # ROE 평균: (150.0 + 45.0) / 2 = 97.5
        assert avg['roe'] == pytest.approx(97.5, rel=1e-2)

    def test_calculate_average_metrics_empty(self, service):
        """빈 리스트 평균 메트릭"""
        avg = service._calculate_average_metrics([])
        assert avg == {}

    def test_calculate_average_metrics_partial_data(self, service):
        """일부 데이터만 있는 경우"""
        stocks = [
            {"symbol": "AAPL", "marketCap": 3000000000000, "pe": 25.5},
            {"symbol": "MSFT", "marketCap": 2500000000000}  # PER 없음
        ]

        avg = service._calculate_average_metrics(stocks)

        # 시가총액은 2개 평균
        assert avg['market_cap'] == pytest.approx(2750000000000, rel=1e-5)

        # PER은 1개만 있으므로 그 값
        assert avg['pe'] == pytest.approx(25.5, rel=1e-2)

        # ROE는 없음
        assert 'roe' not in avg

    # ========================================
    # 펀더멘탈 유사도 계산 테스트
    # ========================================

    def test_calculate_fundamental_similarity_identical(self, service):
        """동일한 펀더멘탈 - 유사도 1.0"""
        stock = {
            "symbol": "TEST",
            "pe": 25.0,
            "roe": 100.0,
            "marketCap": 3000000000000,
            "grossProfitMargin": 40.0
        }

        avg_metrics = {
            "pe": 25.0,
            "roe": 100.0,
            "market_cap": 3000000000000,
            "profit_margin": 40.0
        }

        similarity = service._calculate_fundamental_similarity(stock, avg_metrics)

        # 완전히 동일하면 1.0
        assert similarity == pytest.approx(1.0, rel=1e-2)

    def test_calculate_fundamental_similarity_different(self, service):
        """다른 펀더멘탈 - 유사도 낮음"""
        stock = {
            "symbol": "TEST",
            "pe": 50.0,  # 평균 25.0의 2배
            "roe": 50.0,  # 평균 100.0의 절반
            "marketCap": 1500000000000,  # 평균 3T의 절반
            "grossProfitMargin": 20.0  # 평균 40.0의 절반
        }

        avg_metrics = {
            "pe": 25.0,
            "roe": 100.0,
            "market_cap": 3000000000000,
            "profit_margin": 40.0
        }

        similarity = service._calculate_fundamental_similarity(stock, avg_metrics)

        # 차이가 크므로 유사도 낮음 (0.0 ~ 0.5)
        assert 0.0 <= similarity <= 0.5

    def test_calculate_fundamental_similarity_partial_data(self, service):
        """일부 데이터만 있는 경우"""
        stock = {
            "symbol": "TEST",
            "pe": 25.0,  # PER만 있음
        }

        avg_metrics = {
            "pe": 25.0,
            "roe": 100.0,
            "market_cap": 3000000000000,
            "profit_margin": 40.0
        }

        similarity = service._calculate_fundamental_similarity(stock, avg_metrics)

        # PER만 비교 가능하므로 1.0
        assert similarity == pytest.approx(1.0, rel=1e-2)

    def test_calculate_fundamental_similarity_no_data(self, service):
        """데이터 없는 경우 - 기본값 0.5"""
        stock = {"symbol": "TEST"}
        avg_metrics = {"pe": 25.0}

        similarity = service._calculate_fundamental_similarity(stock, avg_metrics)

        # 비교 불가능하면 기본값 0.5
        assert similarity == 0.5

    # ========================================
    # 캐시 키 생성 테스트
    # ========================================

    def test_get_cache_key_consistent(self, service):
        """동일한 입력 → 동일한 캐시 키"""
        symbols1 = ['AAPL', 'MSFT']
        filters1 = {'pe_ratio_max': 30, 'roe_min': 20}

        symbols2 = ['MSFT', 'AAPL']  # 순서 다름
        filters2 = {'roe_min': 20, 'pe_ratio_max': 30}  # 순서 다름

        key1 = service._get_cache_key(symbols1, filters1)
        key2 = service._get_cache_key(symbols2, filters2)

        # 순서가 달라도 내용이 같으면 동일한 키
        assert key1 == key2

    def test_get_cache_key_different(self, service):
        """다른 입력 → 다른 캐시 키"""
        key1 = service._get_cache_key(['AAPL'], {'pe_ratio_max': 30})
        key2 = service._get_cache_key(['AAPL'], {'pe_ratio_max': 40})
        key3 = service._get_cache_key(['MSFT'], {'pe_ratio_max': 30})

        assert key1 != key2  # 필터 다름
        assert key1 != key3  # 심볼 다름
        assert key2 != key3

    # ========================================
    # 빈 결과 테스트
    # ========================================

    def test_empty_result(self, service):
        """빈 결과 생성"""
        result = service._empty_result(['AAPL'], {'pe_ratio_max': 30})

        assert result['sector_peers'] == []
        assert result['fundamental_similar'] == []
        assert result['ai_insights'] is None
        assert result['chains_count'] == 0
        assert result['metadata']['original_count'] == 1
        assert result['metadata']['filters'] == {'pe_ratio_max': 30}
        assert 'error' in result['metadata']

    # ========================================
    # 섹터 피어 유사도 테스트
    # ========================================

    def test_calculate_peer_similarity(self, service, sample_stocks):
        """섹터 피어 유사도 계산"""
        peer = {
            "symbol": "GOOGL",
            "pe": 27.0,  # 평균 26.75와 유사
            "roe": 100.0,  # 평균 97.5와 유사
            "marketCap": 2600000000000,  # 평균 2.75T와 유사
            "grossProfitMargin": 50.0  # 평균 53.0와 유사
        }

        similarity = service._calculate_peer_similarity(peer, sample_stocks)

        # 평균과 유사하므로 높은 유사도
        assert similarity > 0.8

    # ========================================
    # AI 인사이트 테스트
    # ========================================

    def test_generate_ai_insights(self, service, sample_stocks):
        """AI 인사이트 생성"""
        insights = service._generate_ai_insights(
            original_stocks=sample_stocks,
            sector_peers=[],
            fundamental_similar=[]
        )

        # 인사이트가 생성되어야 함 (기본 메시지)
        assert insights is not None
        assert isinstance(insights, str)
        assert len(insights) > 0

        # 섹터 이름이 포함되어야 함
        assert "Technology" in insights

    def test_generate_ai_insights_empty_stocks(self, service):
        """빈 종목 리스트 - AI 인사이트"""
        insights = service._generate_ai_insights(
            original_stocks=[],
            sector_peers=[],
            fundamental_similar=[]
        )

        # 에러 발생 시 None 반환
        # (빈 리스트로 ZeroDivisionError 가능)
        assert insights is None or isinstance(insights, str)


# ========================================
# 통합 테스트
# ========================================

@pytest.mark.django_db
class TestChainSightIntegration:
    """Chain Sight DNA 통합 테스트 (실제 DB/API 호출)"""

    @pytest.fixture
    def service(self):
        return ChainSightService()

    @pytest.mark.skip(reason="FMP API 호출 필요 (유료)")
    def test_find_related_chains_real_api(self, service):
        """실제 API 호출 테스트 (스킵)"""
        # 실제 API 호출 테스트는 수동으로 실행
        result = service.find_related_chains(
            filtered_symbols=['AAPL', 'MSFT'],
            filters_applied={'pe_ratio_max': 30},
            limit=5,
            use_ai=False
        )

        assert 'sector_peers' in result
        assert 'fundamental_similar' in result
        assert 'chains_count' in result
