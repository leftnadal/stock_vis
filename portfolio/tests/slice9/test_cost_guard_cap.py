"""Slice 9 #43 — CostGuard 슬라이스 cap + 누적 임계 비용 차원 검증.

지시서 §2.3 — 단위 테스트 11건.

- TestSliceCapGuard: 슬라이스 cap $1.00 동작 (7건)
- TestThresholdGuard: 누적 임계 $3.00 동작 (3건)
- TestSlice8Baseline: Slice 8 종결 baseline 보존 (1건)
"""

from __future__ import annotations

import pytest

from portfolio.llm.cost_guard import (
    CostCapExceeded,
    CostGuard,
    CostThresholdExceeded,
)


class TestSliceCapGuard:
    """슬라이스 cap $1.00 검증."""

    def setup_method(self) -> None:
        self.guard = CostGuard()
        self.guard.cumulative_usd = 0.0
        self.guard.slice_usd = 0.0

    def test_slice_cap_default_1_dollar(self) -> None:
        """cap_per_slice 기본값은 $1.00."""
        assert self.guard.cap_per_slice == 1.00

    def test_cap_warning_default_80_percent(self) -> None:
        """cap_warning 기본값은 cap의 80% = $0.80."""
        assert self.guard.cap_warning == 0.80

    def test_record_under_cap_passes(self) -> None:
        """cap 미달 시 정상 기록."""
        self.guard.record_cost(0.50)
        assert self.guard.slice_usd == 0.50
        assert self.guard.cumulative_usd == 0.50

    def test_record_at_cap_passes(self) -> None:
        """cap 정확 도달은 PASS (초과만 차단)."""
        self.guard.record_cost(1.00)
        assert self.guard.slice_usd == 1.00

    def test_record_exceeds_cap_raises(self) -> None:
        """cap 초과 시 CostCapExceeded 발생."""
        self.guard.record_cost(0.80)
        with pytest.raises(CostCapExceeded):
            self.guard.record_cost(0.21)  # 0.80 + 0.21 = 1.01 > 1.00

    def test_warning_at_80_percent(self) -> None:
        """cap 80% ($0.80) 도달 시 경고."""
        self.guard.record_cost(0.80)
        warnings = self.guard.check_warnings()
        assert any("슬라이스 cap 80% 도달" in w for w in warnings)

    def test_reset_for_slice_clears_slice_usd(self) -> None:
        """reset_for_slice가 slice_usd를 0으로 리셋, cumulative_usd는 보존."""
        self.guard.record_cost(0.50)
        self.guard.reset_for_slice("slice9")
        assert self.guard.slice_usd == 0.0
        # cumulative는 유지
        assert self.guard.cumulative_usd == 0.50


class TestThresholdGuard:
    """누적 임계 $4.00 검증 (Slice 11 D-3: $3.00 → $4.00)."""

    def setup_method(self) -> None:
        self.guard = CostGuard()
        self.guard.cumulative_usd = 0.0
        self.guard.slice_usd = 0.0

    def test_threshold_default_4_dollar(self) -> None:
        """threshold 기본값은 $4.00 (Slice 11 D-3 상향)."""
        assert self.guard.threshold == 4.00

    def test_warning_default_3_20(self) -> None:
        """warning 기본값은 threshold의 80% = $3.20."""
        assert self.guard.warning == 3.20

    def test_record_exceeds_threshold_raises(self) -> None:
        """누적 임계 $4.00 초과 시 CostThresholdExceeded 발생."""
        self.guard.cumulative_usd = 3.95
        self.guard.slice_usd = 0.0  # cap 안 건드림
        with pytest.raises(CostThresholdExceeded):
            self.guard.record_cost(0.10)  # 3.95 + 0.10 = 4.05 > 4.00


class TestSlice8Baseline:
    """Slice 8/9 종결 baseline 검증."""

    def test_slice8_cumulative_under_new_threshold(self) -> None:
        """Slice 8 종결 누적 $2.048은 신 임계 $4.00 미달 → 추가 호출 가능."""
        guard = CostGuard()
        guard.cumulative_usd = 2.048
        guard.slice_usd = 0.0
        # 추가 호출 가능 (cap·threshold 모두 안전)
        guard.record_cost(0.10)
        assert guard.cumulative_usd == pytest.approx(2.148)

    def test_slice11_warning_at_3_20(self) -> None:
        """누적 $3.20 도달 시 warning 발동 (Slice 11 D-3 신 임계 80%)."""
        guard = CostGuard()
        guard.cumulative_usd = 3.10
        guard.slice_usd = 0.0
        guard.record_cost(0.15)  # 3.25 > 3.20 warning
        warnings = guard.check_warnings()
        # warning 기준 초과 — 경고 메시지 포함
        # warning은 "⚠ 누적 임계 80% 도달: $X (threshold $Y)" 형식
        assert any("임계 80%" in w or "warning" in w.lower() for w in warnings), warnings
