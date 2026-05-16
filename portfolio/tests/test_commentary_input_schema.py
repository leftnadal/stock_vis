"""Slice 8 Part 1 Step 1 #27 — TimeSeriesContext + MetricResult.time_series 회귀 (4건).

지시서 §Step 1 #3 명시 테스트:
  test_time_series_context_optional_fields
  test_time_series_context_delta_4q_pct
  test_commentary_input_backward_compat
  test_commentary_input_with_time_series
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio.schemas.commentary_input import TimeSeriesContext
from portfolio.schemas.metric_result import MetricResult, MetricTier


def test_time_series_context_optional_fields():
    """모든 window_* 필드 Optional. current만 필수."""
    # current만 채움
    ts_minimal = TimeSeriesContext(current=Decimal("100"))
    assert ts_minimal.current == Decimal("100")
    assert ts_minimal.window_1q is None
    assert ts_minimal.window_4q is None
    assert ts_minimal.window_12q is None

    # 모든 필드 채움
    ts_full = TimeSeriesContext(
        current=Decimal("100"),
        window_1q=Decimal("90"),
        window_4q=Decimal("80"),
        window_12q=Decimal("70"),
    )
    assert ts_full.window_1q == Decimal("90")
    assert ts_full.window_4q == Decimal("80")
    assert ts_full.window_12q == Decimal("70")

    # current 누락 시 ValidationError
    with pytest.raises(Exception):  # pydantic.ValidationError
        TimeSeriesContext()


def test_time_series_context_delta_4q_pct():
    """delta_4q_pct: 정상 계산 + 0 분모 None + 음수 base 처리."""
    # 정상 양수 변화: (100 - 80) / |80| * 100 = 25%
    ts_pos = TimeSeriesContext(current=Decimal("100"), window_4q=Decimal("80"))
    assert ts_pos.delta_4q_pct == Decimal("25")

    # 음수 변화: (75 - 100) / |100| * 100 = -25%
    ts_neg = TimeSeriesContext(current=Decimal("75"), window_4q=Decimal("100"))
    assert ts_neg.delta_4q_pct == Decimal("-25")

    # window_4q None → None
    ts_no_4q = TimeSeriesContext(current=Decimal("100"))
    assert ts_no_4q.delta_4q_pct is None

    # window_4q 0 → None (0 분모 가드)
    ts_zero = TimeSeriesContext(current=Decimal("100"), window_4q=Decimal("0"))
    assert ts_zero.delta_4q_pct is None

    # 음수 base (절댓값 분모): (50 - (-100)) / |−100| * 100 = 150
    ts_neg_base = TimeSeriesContext(
        current=Decimal("50"), window_4q=Decimal("-100")
    )
    assert ts_neg_base.delta_4q_pct == Decimal("150")


def test_commentary_input_backward_compat():
    """기존 fixture (time_series 필드 없음) 로딩 PASS — default None."""
    legacy_data = {
        "metric_id": "roic",
        "metric_display_name": "투하자본수익률",
        "tier": "core",
        "value": "0.283",
        "percentile": "0.88",
        "percentile_scope": "industry",
        "level_tag": "excellent",
        "threshold_applied": "0.15",
        "passed_threshold": True,
    }
    m = MetricResult(**legacy_data)
    assert m.metric_id == "roic"
    assert m.time_series is None  # default None


def test_commentary_input_with_time_series():
    """신규 fixture (time_series 포함) 로딩 + delta_4q_pct 계산 PASS."""
    new_data = {
        "metric_id": "roic",
        "metric_display_name": "투하자본수익률",
        "tier": "core",
        "value": "0.283",
        "percentile": "0.88",
        "percentile_scope": "industry",
        "level_tag": "excellent",
        "threshold_applied": "0.15",
        "passed_threshold": True,
        "time_series": {
            "current": "0.283",
            "window_1q": "0.275",
            "window_4q": "0.250",
            "window_12q": "0.180",
        },
    }
    m = MetricResult(**new_data)
    assert m.time_series is not None
    assert m.time_series.current == Decimal("0.283")
    assert m.time_series.window_4q == Decimal("0.250")
    # delta_4q_pct: (0.283 - 0.250) / 0.250 * 100 = 13.2%
    expected = (Decimal("0.283") - Decimal("0.250")) / Decimal("0.250") * Decimal("100")
    assert m.time_series.delta_4q_pct == expected


def test_metric_result_tier_enum_unchanged():
    """tier enum이 Slice 8 변경에 영향 없음 (backward-compat sanity)."""
    assert MetricTier.CORE == "core"
    assert MetricTier.SUPPORTING == "supporting"
    assert MetricTier.CONTEXT == "context"
