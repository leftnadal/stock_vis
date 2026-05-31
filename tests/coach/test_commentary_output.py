"""Slice 11 Part 2 — CommentaryOutputBase + 6 sub class + ActionItem 검증.

Part 1 `test_commentary_input.py` 미러. 8건.

KPI (Part 2 §4):
- Base 3 필드 (summary / key_observations / confidence) + frozen + extra=forbid
- 6 sub class (E1~E6) 각 진입점별 필드 동작
- ActionItem 정의 보존 (Slice 8 Part 2 #28 호환)
- COMMENTARY_OUTPUT_CLASSES dict 6 entry
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.portfolio.schemas.commentary_output import (
    COMMENTARY_OUTPUT_CLASSES,
    ActionItem,
    CommentaryOutputBase,
    E1Output,
    E2Output,
    E3Output,
    E4Output,
    E5Output,
    E6Output,
)


def _base_kwargs(**overrides) -> dict:
    base = {"summary": "안정 income 포트폴리오", "confidence": "high"}
    base.update(overrides)
    return base


# ============================================================
# Base
# ============================================================


def test_base_required_fields_and_confidence_enum():
    """필수 (summary / confidence) + confidence Literal 3종 (high/medium/low)."""
    # 정상 instantiate (E4가 base만 사용하므로 검증용)
    inst = E4Output(**_base_kwargs())
    assert inst.summary == "안정 income 포트폴리오"
    assert inst.confidence == "high"
    assert inst.key_observations == []
    # 3 confidence 모두 허용
    for c in ("high", "medium", "low"):
        ok = E4Output(**_base_kwargs(confidence=c))
        assert ok.confidence == c
    # 미등록 confidence → ValidationError
    with pytest.raises(ValidationError):
        E4Output(**_base_kwargs(confidence="unknown"))
    # summary empty → ValidationError (min_length=1)
    with pytest.raises(ValidationError):
        E4Output(**_base_kwargs(summary=""))


def test_base_frozen_immutability():
    """frozen=True → 필드 변경 불가."""
    inst = E4Output(**_base_kwargs())
    with pytest.raises(ValidationError):
        inst.summary = "변경 시도"


def test_base_extra_forbid_rejects_unknown_fields():
    """extra='forbid' → 정의되지 않은 필드 거부."""
    with pytest.raises(ValidationError) as exc_info:
        E4Output(**_base_kwargs(unknown_field="x"))
    msg = str(exc_info.value).lower()
    assert "extra" in msg or "forbid" in msg


# ============================================================
# 6 sub class
# ============================================================


def test_six_sub_classes_instantiate_with_specific_fields():
    """E1~E6 모두 진입점별 특화 필드와 함께 instantiate PASS."""
    base = _base_kwargs(confidence="medium")
    ai = ActionItem(title="t", description="설명 description 10+", priority="low")

    e1 = E1Output(**base, action_items=[ai], risk_flags=["concentration"], metrics_table="x")
    assert len(e1.action_items) == 1 and e1.metrics_table == "x"

    e2 = E2Output(**base, quoted_metrics={"yield": 3.45}, metrics_table="")
    assert e2.quoted_metrics["yield"] == 3.45

    e3 = E3Output(**base, action_items=[ai], risk_flags=["hhi_high"])
    assert e3.risk_flags == ["hhi_high"]

    e4 = E4Output(**base)  # base만
    assert e4.confidence == "medium"

    e5 = E5Output(**base, action_items=[ai], quoted_metrics={"beta": 0.62})
    assert e5.quoted_metrics["beta"] == 0.62

    e6 = E6Output(**base, risk_flags=["yield_trap"], quoted_metrics={"score": 8})
    assert e6.risk_flags == ["yield_trap"]


def test_sub_classes_have_base_fields_inherited():
    """모든 sub class는 Base 3 필드를 상속 — summary/key_observations/confidence."""
    for cls in COMMENTARY_OUTPUT_CLASSES.values():
        fields = cls.model_fields
        assert "summary" in fields, cls.__name__
        assert "key_observations" in fields, cls.__name__
        assert "confidence" in fields, cls.__name__


def test_mapping_registers_six_classes():
    """COMMENTARY_OUTPUT_CLASSES — e1~e6 6개 등록 + Part 1 input registry와 키 일관."""
    from apps.portfolio.schemas.commentary_input import COMMENTARY_INPUT_CLASSES

    assert set(COMMENTARY_OUTPUT_CLASSES) == {"e1", "e2", "e3", "e4", "e5", "e6"}
    expected = {
        "e1": E1Output, "e2": E2Output, "e3": E3Output,
        "e4": E4Output, "e5": E5Output, "e6": E6Output,
    }
    assert COMMENTARY_OUTPUT_CLASSES == expected
    # input/output 1:1 키 대응
    assert set(COMMENTARY_INPUT_CLASSES) == set(COMMENTARY_OUTPUT_CLASSES)


def test_sub_class_specific_fields_present():
    """각 sub class의 추가 필드 등록 검증 (지시서 §1.4 매핑표 정합)."""
    assert {"action_items", "risk_flags", "metrics_table"}.issubset(E1Output.model_fields)
    assert {"quoted_metrics", "metrics_table"}.issubset(E2Output.model_fields)
    assert {"action_items", "risk_flags"}.issubset(E3Output.model_fields)
    # E4는 base만 — action_items/risk_flags/quoted_metrics 없음
    assert "action_items" not in E4Output.model_fields
    assert "risk_flags" not in E4Output.model_fields
    assert "quoted_metrics" not in E4Output.model_fields
    assert {"action_items", "quoted_metrics"}.issubset(E5Output.model_fields)
    assert "risk_flags" not in E5Output.model_fields
    assert {"risk_flags", "quoted_metrics"}.issubset(E6Output.model_fields)


# ============================================================
# ActionItem (호환성)
# ============================================================


def test_action_item_definition_unchanged():
    """ActionItem 기존 정의 보존 — Slice 8 Part 2 #28 호환 (호출자 4건)."""
    # 정상 instantiate
    ai = ActionItem(
        title="현금 비중 축소",
        description="포트폴리오 현금 비중이 25%로 과도. 우량 종목 추가 매수 검토.",
        priority="high",
        category="rebalance",
    )
    assert ai.priority == "high"
    assert ai.category == "rebalance"
    # priority/category enum 위반
    with pytest.raises(ValidationError):
        ActionItem(title="t", description="이건 충분히 길어야 합니다 ten chars+", priority="invalid")
    with pytest.raises(ValidationError):
        ActionItem(title="t", description="이건 충분히 길어야 합니다 ten chars+", category="invalid")
    # title min/max 위반
    with pytest.raises(ValidationError):
        ActionItem(title="", description="이건 충분히 길어야 합니다 ten chars+")
