"""Slice 8 Part 1 Step 2 — mock smoke (E3 + E2 fixture v2 schema 유효성).

LLM 호출 0, Pydantic 로딩 + time_series 필드 정합성만 검증.
지시서 §Step 2 #2 명시 4건 + snapshot drift 감지 1건.

KPI:
- 회귀 +2~4건 (smoke 격리)
- $0 비용 (LLM 호출 전혀 없음)
- IDENTICAL 7/7 유지
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from portfolio.schemas.commentary_input import TimeSeriesContext
from portfolio.schemas.metric_result import MetricResult

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _load_metrics(name: str) -> list[MetricResult]:
    """Fixture에서 metrics list 로드 + MetricResult 변환."""
    fixture = _load_fixture(name)
    return [MetricResult(**m) for m in fixture["metrics"]]


# ============================================================
# 지시서 §Step 2 #2 명시 4건
# ============================================================


def test_e3_concentrated_v2_schema_loads():
    """E3 concentrated_portfolio v2 fixture: Pydantic 로딩 PASS, 5 metrics 검증."""
    metrics = _load_metrics("e3_concentrated_v2.json")
    assert len(metrics) == 5
    assert all(isinstance(m, MetricResult) for m in metrics)
    # 첫 metric (roic) 핵심 필드 검증
    roic = metrics[0]
    assert roic.metric_id == "roic"
    assert roic.value == Decimal("0.283")
    assert roic.level_tag == "excellent"


def test_e3_concentrated_v2_time_series_populated():
    """모든 metric에 time_series 필드 존재 + delta_4q_pct 계산 정합."""
    metrics = _load_metrics("e3_concentrated_v2.json")
    for m in metrics:
        assert m.time_series is not None, f"{m.metric_id}: time_series 미설정"
        assert m.time_series.current == m.value, (
            f"{m.metric_id}: time_series.current ({m.time_series.current}) "
            f"!= value ({m.value})"
        )

    # roic delta_4q_pct: (0.283 - 0.250) / 0.250 * 100 = 13.2%
    roic = metrics[0]
    expected = (Decimal("0.283") - Decimal("0.250")) / Decimal("0.250") * Decimal("100")
    assert roic.time_series.delta_4q_pct == expected

    # free_cash_flow_yield: window_12q=null 케이스 (Optional 정상 동작)
    fcf = next(m for m in metrics if m.metric_id == "free_cash_flow_yield")
    assert fcf.time_series.window_12q is None
    assert fcf.time_series.delta_4q_pct is not None  # window_4q는 있음


def test_e2_v2_schema_loads():
    """E2 v2 fixture: Pydantic 로딩 PASS, 3 metrics 검증."""
    metrics = _load_metrics("e2_v2.json")
    assert len(metrics) == 3
    # peg_ratio 핵심
    peg = metrics[0]
    assert peg.metric_id == "peg_ratio"
    assert peg.value == Decimal("1.25")
    assert peg.time_series is not None
    assert peg.time_series.window_4q == Decimal("1.45")


def test_e2_v2_backward_compat():
    """time_series 일부 None 케이스 (earnings_growth window_1q/12q null, roe time_series null) 로딩 PASS."""
    metrics = _load_metrics("e2_v2.json")

    # earnings_growth: window_1q/12q null
    eg = next(m for m in metrics if m.metric_id == "earnings_growth")
    assert eg.time_series is not None
    assert eg.time_series.current == Decimal("0.18")
    assert eg.time_series.window_1q is None
    assert eg.time_series.window_4q == Decimal("0.22")
    assert eg.time_series.window_12q is None
    # delta_4q_pct: (0.18 - 0.22) / |0.22| * 100 = -18.18%
    assert eg.time_series.delta_4q_pct == (Decimal("0.18") - Decimal("0.22")) / Decimal("0.22") * Decimal("100")

    # roe: time_series 자체가 null (backward-compat 완전 누락 케이스)
    roe = next(m for m in metrics if m.metric_id == "roe")
    assert roe.time_series is None


# ============================================================
# 지시서 §Step 2 #3 snapshot 비교 (schema drift 감지)
# ============================================================


def test_e3_concentrated_v2_snapshot_stable():
    """schema dump 결과가 fixture 그대로 (drift 감지 lock-in)."""
    fixture = _load_fixture("e3_concentrated_v2.json")
    metrics = [MetricResult(**m) for m in fixture["metrics"]]

    # Pydantic dump → fixture 원본과 동일 metric_id·value·time_series 비교
    for original, parsed in zip(fixture["metrics"], metrics):
        dumped = parsed.model_dump(mode="json", exclude_none=True)
        # 핵심 필드 라운드트립 확인
        assert dumped["metric_id"] == original["metric_id"]
        assert Decimal(dumped["value"]) == Decimal(original["value"])
        # time_series 라운드트립 (있는 경우)
        if original.get("time_series"):
            assert "time_series" in dumped
            assert Decimal(dumped["time_series"]["current"]) == Decimal(
                original["time_series"]["current"]
            )
