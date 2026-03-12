"""
IndicatorScorer 단위 테스트 (수학 모델 v2.3.2, Section 3)

score_indicator()는 순수 함수로, DB 접근 없이 readings/dates 리스트를 직접 전달.

검증 항목:
  - MAD Floor (중립 반환)
  - support_direction 반전
  - decay 가중치 (최근 데이터 강조)
  - effective_window 축소
  - extreme volatility 플래그 (|z_raw| >= 5.0)
"""

import pytest
from datetime import date, timedelta

from thesis.services.indicator_scorer import score_indicator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dates_back(n, step_days=1):
    """오늘 기준 n개의 날짜 리스트 (오래된 것부터)."""
    today = date.today()
    return [today - timedelta(days=(n - 1 - i) * step_days) for i in range(n)]


def _constant_readings(value, n):
    return [value] * n


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMadFloorNeutral:
    def test_mad_floor_returns_neutral(self):
        """
        모든 reading이 동일한 값이면 MAD≈0 → score=0.0, is_neutral_mad=True.
        """
        readings = _constant_readings(100.0, 20)
        dates = _dates_back(20)

        result = score_indicator(readings, dates, support_direction="positive")

        assert result["score"] == 0.0
        assert result["is_neutral_mad"] is True
        assert result["is_sufficient"] is True


class TestSupportDirection:
    def test_support_direction_flip(self):
        """
        support_direction='negative'이면 점수 부호가 반전되어야 한다.

        단조 증가 데이터: 양의 Z → positive 방향이면 양수, negative이면 음수.
        """
        # 단조 증가: 최신값이 median보다 크므로 양의 z
        readings = list(range(1, 21))  # 1~20
        dates = _dates_back(20)

        result_pos = score_indicator(readings, dates, support_direction="positive")
        result_neg = score_indicator(readings, dates, support_direction="negative")

        assert result_pos["score"] > 0, "positive 방향이면 점수가 양수여야 함"
        assert result_neg["score"] < 0, "negative 방향이면 점수가 음수여야 함"
        assert abs(result_pos["score"]) == pytest.approx(abs(result_neg["score"]), rel=1e-4)


class TestDecayWeighting:
    def test_decay_weights_by_date_gap(self):
        """
        decay 가중치로 인해 최근 데이터가 더 큰 영향을 가져야 한다.

        두 시나리오 모두 동일한 reading 집합을 사용하되 날짜만 다르게 배치한다.
        readings = [1, 5, 1, 5, 1, 5, 1, 5, 1, 100] (양수 편향)

        시나리오 A: 큰 양수값(100)이 '오늘'에 위치 → decay 가중치 최대
        시나리오 B: 큰 양수값(100)이 '30일 전'에 위치 → decay 가중치 최소

        A의 decay-weighted score > B의 decay-weighted score 여야 한다.
        """
        today = date.today()
        n = 10

        # 기본값 패턴: [1, 5, 1, 5, ...] 9개 + 마지막 큰 값 100
        vals = [1.0 if i % 2 == 0 else 5.0 for i in range(n - 1)] + [100.0]

        # 시나리오 A: 순서 그대로 — 큰 값이 today
        dates_a = [today - timedelta(days=(n - 1 - i)) for i in range(n)]
        readings_a = vals[:]  # [1,5,1,5,...,100]

        # 시나리오 B: 순서 반전 — 큰 값이 가장 오래됨
        dates_b = dates_a[:]  # 날짜는 동일 범위
        readings_b = list(reversed(vals))  # [100,5,1,5,...,1]

        result_a = score_indicator(readings_a, dates_a, support_direction="positive", decay=0.80)
        result_b = score_indicator(readings_b, dates_b, support_direction="positive", decay=0.80)

        # 두 결과 모두 MAD neutral이 아님을 확인
        assert result_a["is_neutral_mad"] is False, "시나리오 A: MAD neutral이어선 안 됨"
        assert result_b["is_neutral_mad"] is False, "시나리오 B: MAD neutral이어선 안 됨"

        # 최근 큰 값(A)이 더 높은 점수를 가져야 함
        assert result_a["score"] > result_b["score"], (
            f"최근 이상값 점수({result_a['score']})가 "
            f"먼 과거 이상값 점수({result_b['score']})보다 커야 함"
        )


class TestEffectiveWindow:
    def test_effective_window_shorter_than_param(self):
        """
        10개의 reading이 있고 window=60이면 effective_window=10.
        """
        readings = list(range(1, 11))  # 10개
        dates = _dates_back(10)

        result = score_indicator(readings, dates, support_direction="positive", window=60)

        assert result["effective_window"] == 10

    def test_insufficient_readings_returns_neutral(self):
        """
        5개 미만 reading → is_sufficient=False, score=0.0.
        """
        readings = [10.0, 20.0, 30.0, 40.0]  # 4개
        dates = _dates_back(4)

        result = score_indicator(readings, dates, support_direction="positive")

        assert result["is_sufficient"] is False
        assert result["score"] == 0.0


class TestExtremeVolatility:
    def test_extreme_volatility_flag_at_z5(self):
        """
        |z_raw| >= 5.0이면 is_extreme_vol=True.

        19개의 안정적인 데이터(표준 정규처럼 작은 값) + 마지막에 극단적 이상값.
        """
        # 안정 데이터: 10.0 ± 소폭 변동 (MAD가 작게 유지되도록)
        base = [10.0 + (i % 3) * 0.01 for i in range(19)]  # MAD ≈ 0.01
        outlier = [10.0 + 1000.0]  # 극단값: z_raw 매우 큼

        readings = base + outlier
        dates = _dates_back(20)

        result = score_indicator(readings, dates, support_direction="positive")

        assert result["is_extreme_vol"] is True, (
            f"z_raw={result['raw_z']}이어야 >= 5.0인데 is_extreme_vol={result['is_extreme_vol']}"
        )
        assert abs(result["raw_z"]) >= 5.0
