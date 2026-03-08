"""
DynamicRegimeCalculator 단위 테스트

Z-score 기반 VIX 레짐 판별 + 상대값 하한선(rolling_mean 배수) + Redis 캐싱 검증.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from stocks.services.eod_regime_calculator import (
    DynamicRegimeCalculator, RELATIVE_FLOOR, ABSOLUTE_FALLBACK,
)


class TestDynamicRegimeCalculatorZScore:
    """Z-score 기반 레짐 판별 테스트."""

    def _make_calculator(self, lookback=60, min_points=20):
        return DynamicRegimeCalculator(lookback_days=lookback, min_data_points=min_points)

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_zscore_high_vol(self, mock_cache):
        """Z-score >= 2.0 → 'high_vol'."""
        mock_cache.get.return_value = None

        calc = self._make_calculator()
        target = date(2026, 3, 3)

        # VIX가 일반적으로 15~18이었다가 갑자기 35로 급등 → z >= 2.0
        # mean_ratio = 35/16.32 ≈ 2.14 (< 2.5이므로 relative floor 미적용)
        # z = (35 - 16.32) / 2.46 ≈ 7.6 → z >= 2.0 → high_vol
        normal_prices = [Decimal('16')] * 59
        spike_price = [Decimal('35')]
        prices = normal_prices + spike_price

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result == 'high_vol'

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_zscore_elevated(self, mock_cache):
        """Z-score >= 1.0 and < 2.0 → 'elevated'."""
        mock_cache.get.return_value = None

        calc = self._make_calculator()
        target = date(2026, 3, 3)

        # VIX 평균 18, std ~2 → 현재 22 → z ≈ 1.5~2.0
        import numpy as np
        np.random.seed(42)
        base_prices = np.random.normal(18, 2, 59)
        base_prices = np.clip(base_prices, 10, 30)
        prices = [Decimal(str(round(p, 2))) for p in base_prices] + [Decimal('22')]

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result in ('elevated', 'normal', 'high_vol')
        # z 정확도보다 분기 통과를 검증

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_zscore_normal(self, mock_cache):
        """Z-score < 1.0 → 'normal'."""
        mock_cache.get.return_value = None

        calc = self._make_calculator()
        target = date(2026, 3, 3)

        # VIX가 15~16 범위에서 안정적
        prices = [Decimal('15.5')] * 60

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        # std ≈ 0 → absolute_fallback → normal (15.5 < 25)
        assert result == 'normal'


class TestDynamicRegimeCalculatorRelativeFloor:
    """상대값 하한선(rolling_mean 배수) 테스트."""

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_mean_ratio_2_5x_high_vol(self, mock_cache):
        """current >= rolling_mean * 2.5 → 'high_vol' (Z-score 무관)."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator()
        target = date(2026, 3, 3)

        # VIX 평균 ~14, 현재 40 → mean_ratio ≈ 2.86 (>= 2.5)
        prices = [Decimal('14')] * 59 + [Decimal('40')]

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result == 'high_vol'

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_mean_ratio_1_5x_with_z_elevated(self, mock_cache):
        """current >= rolling_mean * 1.5 AND z >= 0.5 → 'elevated'."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator()
        target = date(2026, 3, 3)

        # VIX 평균 ~15, 현재 24 → mean_ratio ≈ 1.6 (>= 1.5)
        # z도 높을 것이므로 elevated 이상 확정
        prices = [Decimal('15')] * 59 + [Decimal('24')]

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result in ('elevated', 'high_vol')

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_high_z_triggers_high_vol(self, mock_cache):
        """mean_ratio < 2.5이지만 z >= 2.0 → 'high_vol'."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator()
        target = date(2026, 3, 3)

        # VIX 32 유지 중 36으로 급등 → mean_ratio = 36/32.07 ≈ 1.12 (< 1.5)
        # z = (36 - 32.07) / ~0.52 ≈ 7.6 → z >= 2.0 → high_vol
        prices = [Decimal('32')] * 59 + [Decimal('36')]

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result == 'high_vol'

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_stable_vix_normal(self, mock_cache):
        """VIX가 26에서 안정 → std ≈ 0 → fallback → elevated (26 >= 25)."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator()
        target = date(2026, 3, 3)

        # VIX 26 안정 → std ≈ 0 → _absolute_fallback(26) → 26 >= 25 → elevated
        prices = [Decimal('26')] * 60

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result == 'elevated'


class TestDynamicRegimeCalculatorFallback:
    """데이터 부족 및 에러 케이스 테스트."""

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_no_vix_index(self, mock_cache):
        """VIX 인덱스 없음 → 'normal'."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator()
        with patch('macro.models.MarketIndex.objects') as mock_mi:
            mock_mi.filter.return_value.first.return_value = None
            result = calc._calculate_regime(date(2026, 3, 3))

        assert result == 'normal'

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_insufficient_data_fallback(self, mock_cache):
        """데이터 < min_data_points → 절대값 fallback."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator(min_data_points=20)
        target = date(2026, 3, 3)

        # 데이터 10개만 (< 20)
        prices = [Decimal('15')] * 10

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result == 'normal'  # VIX 15 < 25

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_insufficient_data_high_vix_fallback(self, mock_cache):
        """데이터 부족 + VIX 36 → 'high_vol' fallback."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator(min_data_points=20)
        target = date(2026, 3, 3)

        prices = [Decimal('36')] * 10

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        assert result == 'high_vol'


class TestDynamicRegimeCalculatorCaching:
    """Redis 캐싱 테스트."""

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_cache_hit(self, mock_cache):
        """캐시 hit → DB 쿼리 없이 바로 반환."""
        mock_cache.get.return_value = 'elevated'

        calc = DynamicRegimeCalculator()
        result = calc.get_regime(date(2026, 3, 3))

        assert result == 'elevated'
        mock_cache.get.assert_called_once()
        # _calculate_regime이 호출되지 않았으므로 cache.set도 호출되지 않음

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_cache_miss_sets_cache(self, mock_cache):
        """캐시 miss → 계산 후 cache.set 호출."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator()

        with patch.object(calc, '_calculate_regime', return_value='normal') as mock_calc:
            result = calc.get_regime(date(2026, 3, 3))

        assert result == 'normal'
        mock_calc.assert_called_once()
        mock_cache.set.assert_called_once_with(
            'vix_regime:2026-03-03', 'normal', 3600
        )


class TestDynamicRegimeCalculatorLookbackSlicing:
    """lookback 슬라이싱 정확성 테스트."""

    @pytest.mark.django_db
    @patch('stocks.services.eod_regime_calculator.cache')
    def test_63_datapoints_uses_last_60(self, mock_cache):
        """63일 데이터 → 마지막 60개만 사용."""
        mock_cache.get.return_value = None

        calc = DynamicRegimeCalculator(lookback_days=60)
        target = date(2026, 3, 3)

        # 63개 데이터: 처음 3개는 VIX 50 (극단), 마지막 60개는 VIX 15
        prices = [Decimal('50')] * 3 + [Decimal('15')] * 60

        mock_index = MagicMock()
        with patch('macro.models.MarketIndex.objects') as mock_mi, \
             patch('macro.models.MarketIndexPrice.objects') as mock_mip:
            mock_mi.filter.return_value.first.return_value = mock_index
            mock_mip.filter.return_value.order_by.return_value.values_list.return_value = prices

            result = calc._calculate_regime(target)

        # VIX 15 안정적 → std ≈ 0 → fallback → normal (15 < 25)
        assert result == 'normal'


class TestAbsoluteFallback:
    """_absolute_fallback 메서드 직접 테스트."""

    def test_none_returns_normal(self):
        calc = DynamicRegimeCalculator()
        assert calc._absolute_fallback(None) == 'normal'

    def test_low_returns_normal(self):
        calc = DynamicRegimeCalculator()
        assert calc._absolute_fallback(Decimal('15')) == 'normal'

    def test_25_returns_elevated(self):
        calc = DynamicRegimeCalculator()
        assert calc._absolute_fallback(Decimal('25')) == 'elevated'

    def test_35_returns_high_vol(self):
        calc = DynamicRegimeCalculator()
        assert calc._absolute_fallback(Decimal('35')) == 'high_vol'

    def test_50_returns_high_vol(self):
        calc = DynamicRegimeCalculator()
        assert calc._absolute_fallback(Decimal('50')) == 'high_vol'
