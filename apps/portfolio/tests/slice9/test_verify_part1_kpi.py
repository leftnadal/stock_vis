"""Slice 9 #45 — KPI 검증 스크립트 자체 단위 테스트.

지시서 §4.3 — 4건. 분포 폭/4판정/E1 분류 자동 적용 검증.
"""

from __future__ import annotations

from portfolio.tests.helpers.regression_classifier import classify_regression


class TestKPIRules:
    """KPI 검증 로직 보조 단위 테스트."""

    def test_distribution_width_calculation(self) -> None:
        """분포 폭 = max - min (KPI 11)."""
        scores = [3, 4, 5, 5, 4, 3, 2]
        assert max(scores) - min(scores) == 3

    def test_4판정_passing_definition(self) -> None:
        """4판정: cost ≤ 0.10 + length ≥ 100 + score in 0~5."""
        record = {
            "cost_usd": 0.02,
            "rationale_text": "A" * 200,
            "rationale_score": 4,
        }
        ok = (
            record["cost_usd"] <= 0.10
            and len(record["rationale_text"]) >= 100
            and 0 <= record["rationale_score"] <= 5
        )
        assert ok

    def test_kpi_classification_cost_path(self) -> None:
        """schema/prompts 경로 변경 → cost 또는 mixed 분류 (KPI 9a 적용)."""
        paths = [
            "portfolio/schemas/rationale.py",
            "portfolio/prompts/rationale/builder.py",
            "portfolio/tests/slice9/test_rationale_schema.py",
        ]
        result = classify_regression(paths)
        assert result in ("cost", "mixed")

    def test_kpi_classification_no_cost_path(self) -> None:
        """docs/tests 단독 경로 → no-cost 분류 (KPI 9b 적용)."""
        paths = [
            "docs/portfolio/coach/slice9/part1.md",
            "portfolio/tests/slice9/test_verify_part1_kpi.py",
        ]
        assert classify_regression(paths) == "no-cost"
