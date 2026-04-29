"""
Slice 2 Step 1 — E5 schema 단위 테스트.

검증 항목 (v2):
  1. AdjustmentItem 정상 생성
  2. extra=forbid 동작
  3. delta_weight 범위 검증
  4. I2 — decrease + 양수 delta_weight 거절
  5. I2 — info_only + non-zero delta_weight 거절
  6. E5Response no_actionable_intent 정상
  7. I3 — no_actionable_intent + adjustments 모순 거절
  8. E5Response 다중 adjustments
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from portfolio.schemas.llm import AdjustmentItem, E5Response


def test_adjustment_item_valid():
    item = AdjustmentItem(
        ticker="TSLA",
        action="decrease",
        delta_weight=-0.05,
        reason_quote="TSLA 비중 좀 줄여줘",
    )
    assert item.delta_weight == -0.05
    assert item.action == "decrease"


def test_adjustment_item_extra_field_rejected():
    with pytest.raises(ValidationError):
        AdjustmentItem(
            ticker="TSLA",
            action="decrease",
            reason_quote="...",
            extra_field="should_be_rejected",  # type: ignore[call-arg]
        )


def test_adjustment_item_delta_out_of_range():
    with pytest.raises(ValidationError):
        AdjustmentItem(
            ticker="TSLA",
            action="decrease",
            delta_weight=-1.5,  # < -1.0
            reason_quote="너무 많이 줄여",
        )


# I2 검증
def test_adjustment_item_decrease_with_positive_delta_rejected():
    """decrease + 양수 delta_weight는 의미 모순 → 거절."""
    with pytest.raises(
        ValidationError, match="decrease action requires delta_weight"
    ):
        AdjustmentItem(
            ticker="TSLA",
            action="decrease",
            delta_weight=0.05,  # decrease인데 양수
            reason_quote="줄여",
        )


def test_adjustment_item_info_only_with_delta_rejected():
    """info_only + non-zero delta_weight 거절."""
    with pytest.raises(ValidationError, match="info_only action"):
        AdjustmentItem(
            ticker="TSLA",
            action="info_only",
            delta_weight=-0.05,
            reason_quote="TSLA 정보만",
        )


def test_e5_response_no_actionable_intent():
    resp = E5Response(
        adjustments=[],
        confidence=5,
        no_actionable_intent=True,
        ambiguity_notes=None,
    )
    assert len(resp.adjustments) == 0
    assert resp.no_actionable_intent is True


# I3 검증
def test_e5_response_no_intent_with_adjustments_rejected():
    """no_actionable_intent=True인데 adjustments가 있으면 거절."""
    with pytest.raises(
        ValidationError, match="no_actionable_intent=True but adjustments non-empty"
    ):
        E5Response(
            adjustments=[
                AdjustmentItem(
                    ticker="TSLA",
                    action="decrease",
                    delta_weight=-0.05,
                    reason_quote="TSLA 줄여",
                )
            ],
            confidence=3,
            no_actionable_intent=True,  # 모순
        )


def test_e5_response_multiple_adjustments():
    resp = E5Response(
        adjustments=[
            AdjustmentItem(
                ticker="TSLA",
                action="decrease",
                delta_weight=-0.05,
                reason_quote="TSLA 줄여",
            ),
            AdjustmentItem(
                ticker="NVDA",
                action="increase",
                delta_weight=0.05,
                reason_quote="NVDA 늘려",
            ),
        ],
        confidence=4,
    )
    assert len(resp.adjustments) == 2
    assert {a.ticker for a in resp.adjustments} == {"TSLA", "NVDA"}
