"""MP2-SECTOR-CD Slice 1 — classify_cd_state 순수함수 단위 테스트.

DB 무관(순수함수). 사분면 4 + 경계 동률 2(각 축) + null 2(각 축).
baseline = 0.0 (D-SECTOR-CD, STEP 0 실측: rel_strength·momentum_5d 둘 다 0 중심).
"""
from __future__ import annotations

from decimal import Decimal

from apps.market_pulse.constants.sector_cd import (
    CD_MOMENTUM_BASELINE,
    CD_REL_STRENGTH_BASELINE,
    classify_cd_state,
)


class TestClassifyCdStateQuadrants:
    def test_leading_strengthening(self):
        # rel > 0 AND mom > 0 → 주도·강화
        assert classify_cd_state(0.5, 0.5) == "leading_strengthening"

    def test_leading_weakening(self):
        # rel > 0 AND mom < 0 → 주도·둔화
        assert classify_cd_state(0.5, -0.5) == "leading_weakening"

    def test_lagging_improving(self):
        # rel < 0 AND mom > 0 → 부진·개선
        assert classify_cd_state(-0.5, 0.5) == "lagging_improving"

    def test_lagging_deteriorating(self):
        # rel < 0 AND mom < 0 → 부진·악화
        assert classify_cd_state(-0.5, -0.5) == "lagging_deteriorating"


class TestClassifyCdStateBoundary:
    """경계 동률(== baseline)은 하위 상태 귀속 — 낙관 편향 금지."""

    def test_rel_at_baseline_goes_lagging(self):
        # rel == 0 → lead 아님(하위). mom > 0 → lagging_improving
        assert classify_cd_state(0.0, 0.5) == "lagging_improving"
        # rel == 0, mom == 0 → lagging_deteriorating (양축 하위)
        assert classify_cd_state(0.0, 0.0) == "lagging_deteriorating"

    def test_momentum_at_baseline_goes_weakening(self):
        # mom == 0 → up 아님(하위). rel > 0 → leading_weakening
        assert classify_cd_state(0.5, 0.0) == "leading_weakening"
        # rel < 0, mom == 0 → lagging_deteriorating
        assert classify_cd_state(-0.5, 0.0) == "lagging_deteriorating"


class TestClassifyCdStateNull:
    """입력 어느 하나 None → 판단 유보(None). 값 발명 금지."""

    def test_rel_none(self):
        assert classify_cd_state(None, 0.5) is None

    def test_momentum_none(self):
        assert classify_cd_state(0.5, None) is None

    def test_both_none(self):
        assert classify_cd_state(None, None) is None


class TestClassifyCdStateInputTypes:
    def test_accepts_decimal(self):
        # 모델은 Decimal, payload는 float — 둘 다 수용해야 함.
        assert classify_cd_state(Decimal("0.5"), Decimal("-0.5")) == "leading_weakening"
        assert classify_cd_state(Decimal("0.0"), Decimal("0.0")) == "lagging_deteriorating"


def test_baselines_are_zero():
    # 임계 상수 단일소스 값 고정(하드코딩 산재 방지의 회귀 가드).
    assert CD_REL_STRENGTH_BASELINE == 0.0
    assert CD_MOMENTUM_BASELINE == 0.0
