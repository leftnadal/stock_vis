"""
Dynamic Regime Calculator

VIX의 N일 이동평균 대비 Z-score로 시장 레짐을 동적 판별합니다.
절대값 대신 통계적 이상치 탐지 + 상대값(rolling_mean 배수) 방식을 사용합니다.

Z-score = (current_vix - rolling_mean) / rolling_std

레짐 매핑 (Z-score + 상대값 하한선):
  z < 1.0  → 'normal'    (평균 이하~1σ)
  1.0 ≤ z < 2.0 → 'elevated'  (1σ~2σ)
  z ≥ 2.0  → 'high_vol'  (2σ 이상)

상대값 하한선 (Z-score가 낮아도 rolling_mean 대비 배수가 높으면 보정):
  current >= rolling_mean * 2.5 → 'high_vol'
  current >= rolling_mean * 1.5 AND z >= 0.5 → 'elevated'
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from django.core.cache import cache

logger = logging.getLogger(__name__)

# 상대값 하한선: rolling_mean 대비 배수 기준
RELATIVE_FLOOR = {
    'high_vol': 2.5,    # VIX가 평균의 2.5배 이상 → 무조건 high_vol
    'elevated': 1.5,    # VIX가 평균의 1.5배 이상 + z >= 0.5 → elevated
}

# 데이터 부족 시 절대값 fallback
ABSOLUTE_FALLBACK = {
    'elevated': Decimal('25'),
    'high_vol': Decimal('35'),
}


class DynamicRegimeCalculator:
    """
    N일 Rolling Z-score 기반 VIX 레짐 판별기.

    Args:
        lookback_days: Rolling window 크기 (default: 60 거래일 ≈ 3개월)
        min_data_points: 최소 데이터 포인트 (default: 20)
    """

    CACHE_KEY_PREFIX = 'vix_regime'
    CACHE_TTL = 3600  # 1시간

    def __init__(self, lookback_days: int = 60, min_data_points: int = 20):
        self.lookback_days = lookback_days
        self.min_data_points = min_data_points

    def get_regime(self, target_date: date) -> str:
        """
        target_date 기준 VIX 레짐을 Z-score로 판별합니다.
        Redis 캐싱 적용: 동일 target_date에 대해 1시간 캐시.

        Returns:
            'normal' | 'elevated' | 'high_vol'
        """
        cache_key = f"{self.CACHE_KEY_PREFIX}:{target_date.isoformat()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        regime = self._calculate_regime(target_date)
        cache.set(cache_key, regime, self.CACHE_TTL)
        return regime

    def _calculate_regime(self, target_date: date) -> str:
        """Z-score + 상대값 하한선 기반 레짐 계산."""
        try:
            from macro.models import MarketIndexPrice, MarketIndex

            vix_index = MarketIndex.objects.filter(
                symbol__in=['VIX', '^VIX', 'VIXX'],
                category='volatility',
            ).first()

            if not vix_index:
                logger.warning("[DynamicRegimeCalculator] VIX 인덱스 없음, 'normal' 반환")
                return 'normal'

            # lookback_days 거래일 ≈ 캘린더 기준 약 1.5배
            calendar_lookback = int(self.lookback_days * 1.5)
            cutoff_date = target_date - timedelta(days=calendar_lookback)

            prices = list(
                MarketIndexPrice.objects.filter(
                    index=vix_index,
                    date__gt=cutoff_date,
                    date__lte=target_date,
                )
                .order_by('date')
                .values_list('close', flat=True)
            )

            if len(prices) < self.min_data_points:
                logger.warning(
                    f"[DynamicRegimeCalculator] VIX 데이터 부족 "
                    f"({len(prices)}/{self.min_data_points}), "
                    f"절대값 fallback 사용"
                )
                return self._absolute_fallback(prices[-1] if prices else None)

            # 정확히 lookback_days 개수만 슬라이싱
            all_values = np.array([float(p) for p in prices])
            window = all_values[-self.lookback_days:]
            current = window[-1]
            rolling_mean = window.mean()
            rolling_std = window.std(ddof=1)  # 표본 표준편차

            if rolling_std < 0.01:
                logger.warning("[DynamicRegimeCalculator] VIX std ≈ 0, 절대값 fallback")
                return self._absolute_fallback(Decimal(str(current)))

            z_score = (current - rolling_mean) / rolling_std

            # 상대값 하한선: rolling_mean 대비 배수 기반
            mean_ratio = current / rolling_mean if rolling_mean > 0 else 1.0

            if mean_ratio >= RELATIVE_FLOOR['high_vol']:
                regime = 'high_vol'
            elif z_score >= 2.0:
                regime = 'high_vol'
            elif mean_ratio >= RELATIVE_FLOOR['elevated'] and z_score >= 0.5:
                regime = 'elevated'
            elif z_score >= 1.0:
                regime = 'elevated'
            else:
                regime = 'normal'

            logger.info(
                f"[DynamicRegimeCalculator] VIX={current:.1f}, "
                f"mean={rolling_mean:.1f}, std={rolling_std:.1f}, "
                f"z={z_score:.2f}, ratio={mean_ratio:.2f} → {regime}"
            )
            return regime

        except Exception as e:
            logger.warning(f"[DynamicRegimeCalculator] 오류 ({e}), 'normal' 반환")
            return 'normal'

    def _absolute_fallback(self, price) -> str:
        """데이터 부족 시 절대값 기반 fallback (rolling_mean 계산 불가 시)."""
        if price is None:
            return 'normal'
        price = Decimal(str(price))
        if price >= ABSOLUTE_FALLBACK['high_vol']:
            return 'high_vol'
        if price >= ABSOLUTE_FALLBACK['elevated']:
            return 'elevated'
        return 'normal'
