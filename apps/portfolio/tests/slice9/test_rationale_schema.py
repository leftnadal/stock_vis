"""Slice 9 #44 — RationaleRecord / RationaleBatch schema 단위 테스트.

지시서 §1.3 — schema 단위 테스트 3건.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.portfolio.schemas.rationale import RationaleBatch, RationaleRecord


def _minimal_record_kwargs(**overrides):
    kwargs = dict(
        case_id="S01_haiku",
        case_name="S01",
        original_model="claude-haiku-4-5",
        original_commentary="현재 PE 15 이상으로 ...",
        original_specificity_score=3,
        original_specificity_detail={
            "P1_metric_mention": True,
            "P2_threshold": True,
            "P3_action_verb": False,
            "P4_quantitative": False,
            "P5_time_period": True,
        },
        rationale_text="4요소 중 3개 충족 ...",
        rationale_categories=["data_grounding", "threshold_specificity"],
        rationale_score=3,
        cost_usd=0.0264,
        input_tokens=2400,
        output_tokens=480,
        latency_ms=8200,
    )
    kwargs.update(overrides)
    return kwargs


class TestRationaleRecord:
    """RationaleRecord 필드 검증."""

    def test_valid_record_creates(self) -> None:
        record = RationaleRecord(**_minimal_record_kwargs())
        assert record.case_id == "S01_haiku"
        assert record.rationale_model == "claude-sonnet-4-6"
        assert record.estimated_input_tokens == 0  # default

    def test_specificity_score_boundary(self) -> None:
        """original_specificity_score ge=0/le=5 boundary."""
        with pytest.raises(ValidationError):
            RationaleRecord(**_minimal_record_kwargs(original_specificity_score=6))
        with pytest.raises(ValidationError):
            RationaleRecord(**_minimal_record_kwargs(original_specificity_score=-1))
        # boundary in-range
        RationaleRecord(**_minimal_record_kwargs(original_specificity_score=0))
        RationaleRecord(**_minimal_record_kwargs(original_specificity_score=5))

    def test_rationale_score_boundary(self) -> None:
        """rationale_score ge=0/le=5 boundary."""
        with pytest.raises(ValidationError):
            RationaleRecord(**_minimal_record_kwargs(rationale_score=6))
        with pytest.raises(ValidationError):
            RationaleRecord(**_minimal_record_kwargs(rationale_score=-1))


class TestRationaleBatch:
    """RationaleBatch 진행 추적 검증."""

    def test_default_fields(self) -> None:
        batch = RationaleBatch(batch_id=1, case_ids=["S01_haiku", "S01_sonnet"])
        assert batch.completed_count == 0
        assert batch.batch_cost_usd == 0.0
        assert batch.aborted is False
