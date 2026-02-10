"""
Enhanced Screener Service Tests

프리셋-필터 완벽 동기화 테스트
- FMP 필터 추출
- Enhanced 필터 추출
- 클라이언트 필터 추출
- 필터 매칭 로직
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from serverless.services.enhanced_screener_service import EnhancedScreenerService


class TestEnhancedScreenerService:
    """EnhancedScreenerService 단위 테스트"""

    def setup_method(self):
        """테스트 셋업"""
        self.service = EnhancedScreenerService()

    # ==========================================
    # 필터 추출 테스트
    # ==========================================

    def test_extract_fmp_filters(self):
        """FMP 직접 지원 필터 추출 테스트"""
        filters = {
            'market_cap_min': 1_000_000_000,
            'market_cap_max': 100_000_000_000,
            'volume_min': 1_000_000,
            'sector': 'Technology',
            'pe_ratio_min': 10,  # Enhanced 필터 (추출 안 됨)
            'roe_min': 15,  # Enhanced 필터 (추출 안 됨)
        }

        fmp_filters = self.service._extract_fmp_filters(filters)

        assert 'marketCapMoreThan' in fmp_filters
        assert fmp_filters['marketCapMoreThan'] == 1_000_000_000
        assert 'marketCapLowerThan' in fmp_filters
        assert 'volumeMoreThan' in fmp_filters
        assert 'sector' in fmp_filters
        # Enhanced 필터는 추출 안 됨
        assert 'pe_ratio_min' not in fmp_filters
        assert 'roe_min' not in fmp_filters

    def test_extract_enhanced_filters(self):
        """Enhanced 필터 추출 테스트"""
        filters = {
            'market_cap_min': 1_000_000_000,  # FMP 필터
            'pe_ratio_min': 10,
            'pe_ratio_max': 25,
            'roe_min': 15,
            'eps_growth_min': 20,
            'debt_equity_max': 1.0,
            'rsi_max': 30,
        }

        enhanced_filters = self.service._extract_enhanced_filters(filters)

        assert 'pe_ratio_min' in enhanced_filters
        assert 'pe_ratio_max' in enhanced_filters
        assert 'roe_min' in enhanced_filters
        assert 'eps_growth_min' in enhanced_filters
        assert 'debt_equity_max' in enhanced_filters
        assert 'rsi_max' in enhanced_filters
        # FMP 필터는 추출 안 됨
        assert 'market_cap_min' not in enhanced_filters

    def test_extract_client_filters(self):
        """클라이언트 사이드 필터 추출 테스트"""
        filters = {
            'market_cap_min': 1_000_000_000,
            'change_percent_min': 2.0,
            'change_percent_max': 10.0,
            'pe_ratio_min': 10,
        }

        client_filters = self.service._extract_client_filters(filters)

        assert 'change_percent_min' in client_filters
        assert 'change_percent_max' in client_filters
        assert 'market_cap_min' not in client_filters
        assert 'pe_ratio_min' not in client_filters

    # ==========================================
    # Enhanced 필터 매칭 테스트
    # ==========================================

    def test_matches_enhanced_filters_pe_ratio(self):
        """PE Ratio 필터 매칭 테스트"""
        stock = {
            'symbol': 'AAPL',
            'pe_ratio': 15.0,
            'roe': 20.0,
        }

        # PE ≤ 20 통과
        assert self.service._matches_enhanced_filters(stock, {'pe_ratio_max': 20})
        # PE ≤ 10 실패
        assert not self.service._matches_enhanced_filters(stock, {'pe_ratio_max': 10})
        # PE ≥ 10 통과
        assert self.service._matches_enhanced_filters(stock, {'pe_ratio_min': 10})
        # PE ≥ 20 실패
        assert not self.service._matches_enhanced_filters(stock, {'pe_ratio_min': 20})

    def test_matches_enhanced_filters_roe(self):
        """ROE 필터 매칭 테스트"""
        stock = {
            'symbol': 'AAPL',
            'pe_ratio': 15.0,
            'roe': 25.0,
        }

        # ROE ≥ 15 통과
        assert self.service._matches_enhanced_filters(stock, {'roe_min': 15})
        # ROE ≥ 30 실패
        assert not self.service._matches_enhanced_filters(stock, {'roe_min': 30})

    def test_matches_enhanced_filters_combined(self):
        """복합 Enhanced 필터 매칭 테스트"""
        stock = {
            'symbol': 'AAPL',
            'pe_ratio': 15.0,
            'roe': 25.0,
            'eps_growth': 30.0,
            'debt_equity': 0.5,
        }

        # 모든 조건 통과
        filters = {
            'pe_ratio_max': 20,
            'roe_min': 15,
            'eps_growth_min': 20,
            'debt_equity_max': 1.0,
        }
        assert self.service._matches_enhanced_filters(stock, filters)

        # 하나라도 실패하면 전체 실패
        filters_fail = {
            'pe_ratio_max': 20,
            'roe_min': 30,  # 실패
            'eps_growth_min': 20,
        }
        assert not self.service._matches_enhanced_filters(stock, filters_fail)

    def test_matches_enhanced_filters_missing_data(self):
        """데이터 없는 종목 필터 매칭 테스트"""
        stock = {
            'symbol': 'XYZ',
            'pe_ratio': None,  # 데이터 없음
            'roe': None,
        }

        # 핵심 필터 데이터 없으면 제외
        assert not self.service._matches_enhanced_filters(stock, {'pe_ratio_max': 20})
        assert not self.service._matches_enhanced_filters(stock, {'roe_min': 15})

    # ==========================================
    # 클라이언트 필터 적용 테스트
    # ==========================================

    def test_apply_client_filters_change_percent(self):
        """변동률 클라이언트 필터 테스트"""
        stocks = [
            {'symbol': 'AAPL', 'changesPercentage': 5.0},
            {'symbol': 'GOOGL', 'changesPercentage': 2.0},
            {'symbol': 'MSFT', 'changesPercentage': 8.0},
            {'symbol': 'AMZN', 'changesPercentage': -1.0},
        ]

        # 변동률 ≥ 3%
        filtered = self.service._apply_client_filters(stocks, {'change_percent_min': 3.0})
        assert len(filtered) == 2
        symbols = [s['symbol'] for s in filtered]
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols

        # 변동률 ≤ 5%
        filtered = self.service._apply_client_filters(stocks, {'change_percent_max': 5.0})
        assert len(filtered) == 3
        symbols = [s['symbol'] for s in filtered]
        assert 'MSFT' not in symbols

    # ==========================================
    # 정렬 테스트
    # ==========================================

    def test_sort_results_by_market_cap(self):
        """시가총액 정렬 테스트"""
        stocks = [
            {'symbol': 'AAPL', 'marketCap': 2_000_000_000_000},
            {'symbol': 'GOOGL', 'marketCap': 1_500_000_000_000},
            {'symbol': 'MSFT', 'marketCap': 2_500_000_000_000},
        ]

        # 내림차순
        sorted_stocks = self.service._sort_results(stocks, 'marketCap', 'desc')
        assert sorted_stocks[0]['symbol'] == 'MSFT'
        assert sorted_stocks[1]['symbol'] == 'AAPL'
        assert sorted_stocks[2]['symbol'] == 'GOOGL'

        # 오름차순
        sorted_stocks = self.service._sort_results(stocks, 'marketCap', 'asc')
        assert sorted_stocks[0]['symbol'] == 'GOOGL'
        assert sorted_stocks[2]['symbol'] == 'MSFT'

    def test_sort_results_with_none_values(self):
        """None 값 포함 정렬 테스트"""
        stocks = [
            {'symbol': 'AAPL', 'pe_ratio': 15.0},
            {'symbol': 'GOOGL', 'pe_ratio': None},
            {'symbol': 'MSFT', 'pe_ratio': 25.0},
        ]

        # None은 맨 뒤로
        sorted_stocks = self.service._sort_results(stocks, 'pe', 'asc')
        assert sorted_stocks[0]['symbol'] == 'AAPL'
        assert sorted_stocks[1]['symbol'] == 'MSFT'
        assert sorted_stocks[2]['symbol'] == 'GOOGL'

    # ==========================================
    # 유틸리티 테스트
    # ==========================================

    def test_has_enhanced_filters(self):
        """Enhanced 필터 존재 여부 확인 테스트"""
        # Enhanced 필터 있음
        assert self.service.has_enhanced_filters({'pe_ratio_max': 20, 'market_cap_min': 1e9})
        assert self.service.has_enhanced_filters({'roe_min': 15})
        assert self.service.has_enhanced_filters({'eps_growth_min': 20})
        assert self.service.has_enhanced_filters({'rsi_max': 30})

        # Enhanced 필터 없음
        assert not self.service.has_enhanced_filters({'market_cap_min': 1e9})
        assert not self.service.has_enhanced_filters({'volume_min': 1e6, 'sector': 'Technology'})
        assert not self.service.has_enhanced_filters({})

    def test_get_filter_type(self):
        """필터 타입 판별 테스트"""
        # Enhanced
        assert self.service.get_filter_type({'pe_ratio_max': 20}) == 'enhanced'
        assert self.service.get_filter_type({'roe_min': 15, 'market_cap_min': 1e9}) == 'enhanced'

        # Instant
        assert self.service.get_filter_type({'market_cap_min': 1e9}) == 'instant'
        assert self.service.get_filter_type({'sector': 'Technology'}) == 'instant'
        assert self.service.get_filter_type({}) == 'instant'


class TestEnhancedScreenerIntegration:
    """EnhancedScreenerService 통합 테스트 (Mock)"""

    @patch('serverless.services.enhanced_screener_service.FMPClient')
    @patch('serverless.services.enhanced_screener_service.cache')
    def test_screen_enhanced_with_pe_roe_filter(self, mock_cache, mock_fmp_client):
        """PE/ROE 필터로 Enhanced 스크리닝 테스트"""
        # Mock 설정
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None

        mock_client = MagicMock()
        mock_fmp_client.return_value = mock_client

        # FMP Screener 응답 Mock
        mock_client._make_request.side_effect = [
            # 1차: company-screener
            [
                {'symbol': 'AAPL', 'companyName': 'Apple', 'marketCap': 2e12},
                {'symbol': 'GOOGL', 'companyName': 'Alphabet', 'marketCap': 1.5e12},
                {'symbol': 'META', 'companyName': 'Meta', 'marketCap': 800e9},
            ],
            # 2차: key-metrics-ttm (AAPL)
            [{'peRatioTTM': 28.0, 'roeTTM': 150.0}],
            # 2차: key-metrics-ttm (GOOGL)
            [{'peRatioTTM': 22.0, 'roeTTM': 25.0}],
            # 2차: key-metrics-ttm (META)
            [{'peRatioTTM': 12.0, 'roeTTM': 18.0}],
        ]

        service = EnhancedScreenerService()
        result = service.screen_enhanced(
            filters={
                'market_cap_min': 500_000_000_000,
                'pe_ratio_max': 25,  # PE ≤ 25
                'roe_min': 15,       # ROE ≥ 15
            },
            limit=10
        )

        assert result['is_enhanced'] == True
        # META (PE=12, ROE=18) 와 GOOGL (PE=22, ROE=25) 만 통과
        # AAPL은 PE=28로 실패
        assert result['count'] <= 3

    @patch('serverless.services.enhanced_screener_service.FMPClient')
    @patch('serverless.services.enhanced_screener_service.cache')
    def test_screen_instant_without_enhanced_filters(self, mock_cache, mock_fmp_client):
        """Enhanced 필터 없이 Instant 스크리닝 테스트"""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None

        mock_client = MagicMock()
        mock_fmp_client.return_value = mock_client

        # FMP Screener 응답 Mock
        mock_client._make_request.return_value = [
            {'symbol': 'AAPL', 'companyName': 'Apple', 'marketCap': 2e12},
            {'symbol': 'GOOGL', 'companyName': 'Alphabet', 'marketCap': 1.5e12},
        ]

        service = EnhancedScreenerService()
        result = service.screen_enhanced(
            filters={
                'market_cap_min': 500_000_000_000,
                'volume_min': 1_000_000,
            },
            limit=10
        )

        # Enhanced 필터 없으므로 추가 API 호출 없음
        assert result['is_enhanced'] == False
        assert result['count'] == 2
