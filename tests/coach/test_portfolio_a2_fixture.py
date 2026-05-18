"""Slice 11 Step 0 §3 — portfolio_a2 fixture + E6 mock 검증.

KPI:
- schema validation PASS
- 5 종목 × 분석 결과 1:1 매칭
- preset 차별성 (GARP/focused 제외, income preset)

테스트 4건.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from portfolio.schemas.llm_outputs import E6ComparisonResponse

FIXTURE_DIR = Path(__file__).resolve().parents[1].parent / "portfolio" / "tests" / "fixtures" / "coach"
PORTFOLIO_PATH = FIXTURE_DIR / "portfolio_a2.json"
E6_ANALYSIS_PATH = FIXTURE_DIR / "portfolio_a2_e6_analysis.json"


@pytest.fixture(scope="module")
def portfolio_a2():
    with open(PORTFOLIO_PATH, encoding="utf-8") as fp:
        return json.load(fp)


@pytest.fixture(scope="module")
def e6_analysis():
    with open(E6_ANALYSIS_PATH, encoding="utf-8") as fp:
        return json.load(fp)


def test_portfolio_a2_schema_and_weights_sum(portfolio_a2):
    """필수 키 존재 + holdings 비중 합 = 1.0 + 5 종목."""
    for key in (
        "fixture_id",
        "preset_id",
        "holdings",
        "portfolio_metrics",
        "analysis_summary",
    ):
        assert key in portfolio_a2, f"missing key: {key}"
    holdings = portfolio_a2["holdings"]
    assert len(holdings) == 5
    total = sum(h["weight"] for h in holdings)
    assert abs(total - 1.0) < 1e-6
    # 1 ETF + 4 stocks (지시서 권장)
    etf_count = sum(1 for h in holdings if h.get("asset_class") == "etf")
    stock_count = sum(1 for h in holdings if h.get("asset_class") == "stock")
    assert etf_count == 1 and stock_count == 4


def test_portfolio_a2_preset_differs_from_garp_focused(portfolio_a2):
    """기존 GARP/focused와 preset 차별 — income preset 채택."""
    assert portfolio_a2["preset_id"] == "income"
    assert portfolio_a2["preset_id"] not in ("garp", "focused")
    assert portfolio_a2["analysis_summary"]["preset_id"] == "income"


def test_e6_analysis_validates_against_response_schema(e6_analysis):
    """mock e6_response가 E6ComparisonResponse Pydantic 스키마 통과."""
    mock = e6_analysis["e6_response_mock"]
    # Pydantic 검증
    parsed = E6ComparisonResponse.model_validate(mock)
    assert parsed.headline
    assert 1 <= len(parsed.key_changes) <= 5
    assert len(parsed.action_items) >= 0


def test_a2_adjustments_align_with_portfolio_tickers(portfolio_a2, e6_analysis):
    """adjustments의 ticker는 portfolio holdings에 존재(decrease/remove) 또는 신규(add).

    A2는 portfolio_a2 holdings를 baseline으로 e6_analysis adjustments 적용.
    """
    holding_tickers = {h["ticker"] for h in portfolio_a2["holdings"]}
    for adj in e6_analysis["adjustments"]:
        ticker = adj["ticker"]
        action = adj["action"]
        if action in ("decrease", "increase", "remove"):
            assert ticker in holding_tickers, (
                f"{action} 대상 {ticker}는 baseline holdings에 존재해야 함"
            )
        elif action == "add":
            assert ticker not in holding_tickers, (
                f"add 대상 {ticker}는 baseline holdings에 부재해야 함"
            )
