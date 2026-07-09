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
    resolve_official_cd_state,
)

# 짧은 상태 별칭(가독).
A = "leading_strengthening"
B = "leading_weakening"
C = "lagging_improving"
D = "lagging_deteriorating"


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


class TestResolveOfficialCdState:
    """CD-STAB Slice B — 2일 히스테리시스 리플레이(무상태). 반환 = 공식 상태 시퀀스."""

    def test_seed_first_state(self):
        # 첫날 raw = 초기 공식.
        assert resolve_official_cd_state([A]) == [A]

    def test_one_day_blip_suppressed(self):
        # A 유지 중 B 1일 블립 → 공식은 A 유지(전환 안 함).
        assert resolve_official_cd_state([A, A, B, A, A]) == [A, A, A, A, A]

    def test_two_day_confirm_transition(self):
        # B가 2연속 → 2일째 공식 전환. 전환 인정일 포함 확인.
        assert resolve_official_cd_state([A, B, B, B]) == [A, A, B, B]

    def test_candidate_reset_on_change(self):
        # 후보 교란 A→B→C→C: B는 1일뿐(리셋), C가 2연속 확정.
        assert resolve_official_cd_state([A, B, C, C]) == [A, A, A, C]

    def test_candidate_reset_back_to_official(self):
        # A→B→A(공식복귀)→B→B: B 카운터 리셋됐다가 재확정.
        assert resolve_official_cd_state([A, B, A, B, B]) == [A, A, A, A, B]

    def test_none_defends_official(self):
        # raw None인 날: 공식 유지(유보값으로 전환 안 함) + 후보 리셋.
        assert resolve_official_cd_state([A, B, None, B, B]) == [A, A, A, A, B]

    def test_seed_skips_leading_none(self):
        # 선행 None은 시드 전 — 첫 non-None이 시드.
        assert resolve_official_cd_state([None, None, A, A]) == [None, None, A, A]

    def test_early_pollution_washed_out(self):
        # 초기 floor-0 오염(가짜 D)이 있어도 2일 메모리로 현재 시점 전에 세척 — 현재 공식은 A.
        seq = [D, D, A, A, A, A, A]  # 초기 D 후 A가 지속
        official = resolve_official_cd_state(seq)
        assert official[-1] == A

    def test_returns_same_length(self):
        seq = [A, B, C, D, A]
        assert len(resolve_official_cd_state(seq)) == len(seq)

    def test_empty_sequence(self):
        assert resolve_official_cd_state([]) == []
