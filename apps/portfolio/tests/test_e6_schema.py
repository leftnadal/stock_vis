"""E6 schema 단위 테스트 (Slice 4 Step 1).

E6Request / E6ComparisonResponse / E6KeyChange / E6ChangeAspect 검증.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from portfolio.schemas.llm import AdjustmentItem, E6Request
from portfolio.schemas.llm_outputs import (
    E6ChangeAspect,
    E6ComparisonResponse,
    E6KeyChange,
)


def _sample_adjustment() -> AdjustmentItem:
    """단일 valid AdjustmentItem 헬퍼 (실제 AdjustmentItem schema 기준)."""
    return AdjustmentItem(
        ticker="TSLA",
        action="decrease",
        delta_weight=-0.10,
        target_weight=None,
        reason_quote="TSLA 비중 좀 줄여줘",
    )


def test_e6_request_minimal_valid():
    """analysis_context + adjustments(1개) 최소 충족 시 유효. user_intent None."""
    req = E6Request(
        analysis_context={"preset_id": "garp", "holdings": []},
        adjustments=[_sample_adjustment()],
    )
    assert req.user_intent is None
    assert req.session_id is None
    assert len(req.adjustments) == 1
    assert req.adjustments[0].ticker == "TSLA"


def test_e6_request_empty_adjustments_invalid():
    """adjustments 빈 리스트는 invalid (min_length=1)."""
    with pytest.raises(ValidationError):
        E6Request(
            analysis_context={"preset_id": "garp"},
            adjustments=[],
        )


def test_e6_request_extra_field_forbidden():
    """extra='forbid' — 정의되지 않은 필드 거절."""
    with pytest.raises(ValidationError):
        E6Request(
            analysis_context={"preset_id": "garp"},
            adjustments=[_sample_adjustment()],
            unknown_field="hack",
        )


def test_e6_response_full_valid():
    """E6ComparisonResponse 모든 필드 정상 + key_changes 2개."""
    resp = E6ComparisonResponse(
        headline="원본 대비 위험은 낮아지고 성장 노출은 유지됩니다",
        before_summary="기술주 집중도 70%로 단일 섹터 편중. 변동성 높은 구성.",
        after_summary="기술주 55%로 완화, 디펜시브 종목 추가로 균형 개선.",
        key_changes=[
            E6KeyChange(
                aspect=E6ChangeAspect.ALLOCATION,
                description="테슬라 비중 20% → 10% 축소",
            ),
            E6KeyChange(
                aspect="risk", description="단일 섹터 집중도 위험이 완화됩니다"
            ),
        ],
        risk_assessment="포트폴리오 변동성이 약간 낮아지고 하방 리스크가 완화됩니다.",
        closing_remarks="수익률 상한선은 일부 양보될 수 있으나 안정성 향상입니다.",
    )
    assert len(resp.key_changes) == 2
    # Literal/Enum string 호환성 검증
    assert resp.key_changes[0].aspect == E6ChangeAspect.ALLOCATION
    assert resp.key_changes[1].aspect == E6ChangeAspect.RISK


def test_e6_keychange_invalid_aspect():
    """aspect 가 정의된 5종 외 문자열일 때 거절."""
    with pytest.raises(ValidationError):
        E6KeyChange(
            aspect="invalid_aspect_value", description="설명 충분히 길게 작성됨"
        )
