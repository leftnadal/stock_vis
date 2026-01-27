"""
Market Movers Indicators 유닛 테스트

Phase 1 + Phase 2 지표 계산 로직 검증
"""
import unittest
from decimal import Decimal
from serverless.services.indicators import IndicatorCalculator


class TestIndicatorCalculator(unittest.TestCase):
    """IndicatorCalculator 테스트"""

    def setUp(self):
        self.calc = IndicatorCalculator()

    # ========================================
    # Phase 1: RVOL
    # ========================================

    def test_calculate_rvol_normal(self):
        """RVOL 정상 계산"""
        current = 10_000_000
        historical = [5_000_000] * 20
        result = self.calc.calculate_rvol(current, historical)

        self.assertEqual(result, Decimal('2.00'))

    def test_calculate_rvol_insufficient_data(self):
        """RVOL 데이터 부족"""
        current = 10_000_000
        historical = [5_000_000] * 5  # 10개 미만
        result = self.calc.calculate_rvol(current, historical)

        self.assertIsNone(result)

    def test_calculate_rvol_zero_volumes(self):
        """RVOL 평균이 0인 경우 (모든 거래량이 0)"""
        current = 10_000_000
        historical = [0] * 20
        result = self.calc.calculate_rvol(current, historical)

        # 0인 거래량은 필터링되므로 데이터 부족으로 None 반환
        self.assertIsNone(result)

    # ========================================
    # Phase 1: Trend Strength
    # ========================================

    def test_calculate_trend_strength_bullish(self):
        """추세 강도 - 강한 상승"""
        result = self.calc.calculate_trend_strength(100, 110, 100, 110)
        self.assertEqual(result, Decimal('1.00'))

    def test_calculate_trend_strength_bearish(self):
        """추세 강도 - 강한 하락"""
        result = self.calc.calculate_trend_strength(110, 110, 100, 100)
        self.assertEqual(result, Decimal('-1.00'))

    def test_calculate_trend_strength_no_range(self):
        """추세 강도 - 변동 없음"""
        result = self.calc.calculate_trend_strength(100, 100, 100, 100)
        self.assertEqual(result, Decimal('0.00'))

    # ========================================
    # Phase 2: Sector Alpha
    # ========================================

    def test_calculate_sector_alpha_positive(self):
        """섹터 알파 - 양수 (종목이 섹터보다 우수)"""
        result = self.calc.calculate_sector_alpha(5.0, 2.0)
        self.assertEqual(result, Decimal('3.00'))

    def test_calculate_sector_alpha_negative(self):
        """섹터 알파 - 음수 (종목이 섹터보다 부진)"""
        result = self.calc.calculate_sector_alpha(-2.0, 1.0)
        self.assertEqual(result, Decimal('-3.00'))

    def test_calculate_sector_alpha_zero(self):
        """섹터 알파 - 0 (종목과 섹터 동일)"""
        result = self.calc.calculate_sector_alpha(2.5, 2.5)
        self.assertEqual(result, Decimal('0.00'))

    # ========================================
    # Phase 2: ETF Sync Rate
    # ========================================

    def test_calculate_etf_sync_perfect_correlation(self):
        """ETF 동행률 - 완전 동조"""
        stock = [100.0 + i for i in range(20)]
        etf = [50.0 + i * 0.5 for i in range(20)]
        result = self.calc.calculate_etf_sync_rate(stock, etf)

        self.assertEqual(result, Decimal('1.00'))

    def test_calculate_etf_sync_no_correlation(self):
        """ETF 동행률 - 무관"""
        stock = [100.0, 101.0, 99.0, 102.0, 98.0] * 4
        etf = [50.0] * 20  # 변동 없음
        result = self.calc.calculate_etf_sync_rate(stock, etf)

        self.assertIsNone(result)  # 표준편차 0

    def test_calculate_etf_sync_insufficient_data(self):
        """ETF 동행률 - 데이터 부족"""
        stock = [100.0] * 5
        etf = [50.0] * 5
        result = self.calc.calculate_etf_sync_rate(stock, etf)

        self.assertIsNone(result)

    # ========================================
    # Phase 2: Volatility Percentile
    # ========================================

    def test_calculate_volatility_percentile_high(self):
        """변동성 백분위 - 최고"""
        hist = [1.0, 1.5, 2.0, 2.5, 3.0] * 4  # 20개
        result = self.calc.calculate_volatility_percentile(3.5, hist)

        self.assertEqual(result, 100)

    def test_calculate_volatility_percentile_low(self):
        """변동성 백분위 - 최저"""
        hist = [1.0, 1.5, 2.0, 2.5, 3.0] * 4
        result = self.calc.calculate_volatility_percentile(0.5, hist)

        self.assertEqual(result, 0)

    def test_calculate_volatility_percentile_median(self):
        """변동성 백분위 - 중간"""
        hist = [1.0, 2.0, 3.0, 4.0, 5.0] * 4
        result = self.calc.calculate_volatility_percentile(3.0, hist)

        # 정확한 백분위는 데이터에 따라 달라짐
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 100)

    def test_calculate_volatility_percentile_insufficient_data(self):
        """변동성 백분위 - 데이터 부족"""
        hist = [1.0] * 10  # 20개 미만
        result = self.calc.calculate_volatility_percentile(2.0, hist)

        self.assertIsNone(result)

    # ========================================
    # Display Formatters
    # ========================================

    def test_format_rvol_display(self):
        """RVOL 표시 포맷"""
        self.assertEqual(self.calc.format_rvol_display(Decimal('2.50')), '2.5x')
        self.assertEqual(self.calc.format_rvol_display(None), 'N/A')

    def test_format_trend_display(self):
        """추세 강도 표시 포맷"""
        self.assertEqual(self.calc.format_trend_display(Decimal('0.85')), '▲0.85')
        self.assertEqual(self.calc.format_trend_display(Decimal('-0.67')), '▼-0.67')
        self.assertEqual(self.calc.format_trend_display(None), 'N/A')

    def test_format_sector_alpha_display(self):
        """섹터 알파 표시 포맷"""
        self.assertEqual(self.calc.format_sector_alpha_display(Decimal('2.50')), '+2.5%')
        self.assertEqual(self.calc.format_sector_alpha_display(Decimal('-1.30')), '-1.3%')
        self.assertEqual(self.calc.format_sector_alpha_display(None), 'N/A')

    def test_format_etf_sync_display(self):
        """ETF 동행률 표시 포맷"""
        self.assertEqual(self.calc.format_etf_sync_display(Decimal('0.85')), '0.85')
        self.assertEqual(self.calc.format_etf_sync_display(None), 'N/A')

    def test_format_volatility_percentile_display(self):
        """변동성 백분위 표시 포맷"""
        self.assertEqual(self.calc.format_volatility_percentile_display(87), '87')
        self.assertEqual(self.calc.format_volatility_percentile_display(None), 'N/A')


if __name__ == '__main__':
    unittest.main()
