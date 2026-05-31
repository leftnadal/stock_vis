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
    with pytest.raises(ValidationError, match="decrease action requires delta_weight"):
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


# ============================================================
# E2 (DiagnosticCard 4요소) — Slice 3
# ============================================================
from portfolio.schemas.llm import E2DiagnosticCard, E2Request, E2Response


def test_e2_diagnostic_card_valid():
    card = E2DiagnosticCard(
        summary="GARP 적합도 양호. 균형 잡힌 포트폴리오 분석.",
        strengths=["P/E 12.5 적정 수준", "ROE 18% 우수한 수익성"],
        weaknesses=["배당수익률 1.2% 다소 낮음"],
        actions=["분기별 ROE 모니터링 권장"],
    )
    assert card.summary.startswith("GARP")
    assert len(card.strengths) == 2


def test_e2_diagnostic_card_extra_field_rejected():
    with pytest.raises(ValidationError):
        E2DiagnosticCard(
            summary="포트폴리오 요약 텍스트 길이 충분합니다.",
            strengths=["a" * 20],
            weaknesses=["a" * 20],
            actions=["a" * 20],
            extra_field="rejected",
        )


def test_e2_diagnostic_card_short_summary_rejected():
    with pytest.raises(ValidationError):
        E2DiagnosticCard(
            summary="짧음",  # < 20 chars
            strengths=["a" * 20],
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )


def test_e2_diagnostic_card_empty_list_rejected():
    """strengths/weaknesses/actions 빈 리스트 거절."""
    with pytest.raises(ValidationError):
        E2DiagnosticCard(
            summary="포트폴리오 요약 텍스트 충분히 길게 작성합니다.",
            strengths=[],
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )


def test_e2_diagnostic_card_short_item_rejected():
    """리스트 항목 10자 미만 거절 (completeness 자동 측정)."""
    with pytest.raises(ValidationError, match="too short"):
        E2DiagnosticCard(
            summary="포트폴리오 요약 텍스트 충분히 길게 작성하기.",
            strengths=["짧음"],  # < 10 chars
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )


def test_e2_diagnostic_card_too_many_items_rejected():
    """리스트 항목 6개 이상 거절."""
    with pytest.raises(ValidationError):
        E2DiagnosticCard(
            summary="요약 텍스트 충분히 긴 길이로 작성합니다.",
            strengths=["item " + "x" * 15] * 6,  # 6개
            weaknesses=["a" * 20],
            actions=["a" * 20],
        )
