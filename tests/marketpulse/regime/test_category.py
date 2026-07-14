"""L2 국면 카테고리 순수 함수 회귀 — Slice C-core.

계약: regime enum 전수 → {key, label(enum 표시명 재사용)}. 미지 값 = 명시적 에러(조용한 null 금지).
"""
from __future__ import annotations

import pytest

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime.category import categorize_or_none, categorize_regime

Regime = RegimeSnapshot.Regime


@pytest.mark.parametrize("value", list(Regime.values))
def test_every_regime_value_maps_surjectively(value):
    """enum 전수 매핑(전사) — label = enum 공식 표시명 재사용(단일 출처)."""
    cat = categorize_regime(value)
    assert cat["key"] == value
    assert cat["label"] == Regime(value).label
    assert cat["label"]  # 비어있지 않음


def test_unknown_value_raises_not_silent_null():
    with pytest.raises(ValueError, match="미지 regime 값"):
        categorize_regime("SOME_FUTURE_REGIME")


def test_categorize_or_none_handles_empty():
    assert categorize_or_none(None) is None
    assert categorize_or_none("") is None
    assert categorize_or_none("CRISIS") == {"key": "CRISIS", "label": Regime.CRISIS.label}


def test_crisis_label_is_factual_not_similarity_claim():
    """CRISIS 게이트: 태그 label은 사실 분류명('위기')일 뿐 유사성 주장 문구가 아님."""
    cat = categorize_regime("CRISIS")
    assert cat["label"] == "위기"
    # '유사'·'닮'·'같은' 류 유사성 주장 어휘가 태그에 없음
    assert not any(w in cat["label"] for w in ("유사", "닮", "같"))
