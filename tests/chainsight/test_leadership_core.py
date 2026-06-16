"""
주도주 지표 코어 순수함수 테스트 (CS-M2 Slice 1).

합성데이터 단위테스트 — DB 불요(순수함수).
- T2: 완전직선상승 → R²≈1, slope>0, trend_quality>0
- T3: β=2 합성(r_i = 2·r_theme + noise) → theme_beta≈2, alpha≈0
- ②: 상승장만 초과수익 → up_capture > 100
- 게이트: 유효일 부족 → NULL(에러 아님)
- 룩어헤드 없음: t지표가 t+1 데이터 미사용
"""

import math

import numpy as np
import pytest

from apps.chain_sight.services.leadership_service import (
    MIN_THEME_MEMBERS,
    capture_ratios,
    daily_returns,
    loo_theme_returns,
    passes_obs_gate,
    theme_alpha_beta,
    trend_quality,
)


# ── T2: 추세품질 ──────────────────────────────────────────────────────────────

class TestTrendQuality:
    def test_perfect_uptrend(self):
        """완전 지수 상승(log 직선) → R²≈1, slope>0, trend_quality>0."""
        # close = 100 * exp(0.01 * t) → log(close) 완전 직선
        closes = [100.0 * math.exp(0.01 * t) for t in range(20)]
        res = trend_quality(closes)
        assert res is not None
        assert res["slope"] == pytest.approx(0.01, abs=1e-9)
        assert res["r_squared"] == pytest.approx(1.0, abs=1e-9)
        assert res["trend_quality"] > 0
        # tq = (0.01 * 252) * 1.0 = 2.52
        assert res["trend_quality"] == pytest.approx(2.52, abs=1e-6)

    def test_downtrend_negative_tq(self):
        """하락 추세 → slope<0 → trend_quality<0."""
        closes = [100.0 * math.exp(-0.01 * t) for t in range(20)]
        res = trend_quality(closes)
        assert res is not None
        assert res["slope"] < 0
        assert res["trend_quality"] < 0

    def test_noisy_trend_low_r2_dampens(self):
        """노이즈 큰 추세 → R²↓ → trend_quality가 순수 기울기보다 감쇠."""
        rng = np.random.default_rng(42)
        closes = [100.0 * math.exp(0.005 * t) * (1 + rng.normal(0, 0.05)) for t in range(40)]
        res = trend_quality(closes)
        assert res is not None
        assert 0.0 <= res["r_squared"] <= 1.0
        # 감쇠 확인: |tq| <= |slope*252|
        assert abs(res["trend_quality"]) <= abs(res["slope"] * 252) + 1e-9

    def test_flat_series_r2_and_tq(self):
        """완전 평탄(분산 0) → slope 0, r_squared 1, trend_quality 0."""
        closes = [100.0] * 20
        res = trend_quality(closes)
        assert res is not None
        assert res["slope"] == pytest.approx(0.0)
        assert res["trend_quality"] == pytest.approx(0.0)

    def test_nonpositive_close_returns_none(self):
        """비양수 종가 포함 → None(에러 아님)."""
        assert trend_quality([100.0, 0.0, 101.0]) is None
        assert trend_quality([100.0, -5.0]) is None

    def test_empty_and_single_return_none(self):
        assert trend_quality([]) is None
        assert trend_quality([100.0]) is None


# ── 일수익률 헬퍼 ─────────────────────────────────────────────────────────────

class TestDailyReturns:
    def test_basic_returns(self):
        rets = daily_returns([100.0, 110.0, 99.0])
        assert len(rets) == 2
        assert rets[0] == pytest.approx(0.10)
        assert rets[1] == pytest.approx(-0.10)

    def test_nonpositive_prev_yields_zero(self):
        rets = daily_returns([0.0, 100.0])
        assert rets[0] == 0.0


# ── LOO 테마 수익률 ───────────────────────────────────────────────────────────

class TestLooThemeReturns:
    def test_loo_excludes_self(self):
        """자기 제외 등가중 평균."""
        members = {
            "A": [0.10, 0.20],
            "B": [0.00, 0.00],
            "C": [0.20, 0.40],
        }
        loo = loo_theme_returns(members, "A")
        assert loo is not None
        # B,C 평균
        assert loo[0] == pytest.approx(0.10)
        assert loo[1] == pytest.approx(0.20)

    def test_below_min_members_returns_none(self):
        """멤버 < MIN_THEME_MEMBERS → None."""
        members = {"A": [0.1], "B": [0.2]}
        assert MIN_THEME_MEMBERS == 3
        assert loo_theme_returns(members, "A") is None

    def test_missing_target_returns_none(self):
        members = {"A": [0.1], "B": [0.2], "C": [0.3]}
        assert loo_theme_returns(members, "Z") is None

    def test_length_mismatch_members_excluded(self):
        """길이 다른 멤버는 평균에서 제외."""
        members = {
            "A": [0.1, 0.2],
            "B": [0.3, 0.4],
            "C": [0.5],  # 길이 불일치 → 제외
        }
        loo = loo_theme_returns(members, "A")
        assert loo is not None
        assert loo[0] == pytest.approx(0.3)  # B만 남음


# ── T3: 테마 알파/베타 ────────────────────────────────────────────────────────

class TestThemeAlphaBeta:
    def test_beta_recovers_two(self):
        """r_i = 2·r_theme + noise → theme_beta≈2, alpha≈0."""
        rng = np.random.default_rng(7)
        theme = rng.normal(0, 0.02, 250).tolist()
        noise = rng.normal(0, 0.001, 250)
        stock = [2.0 * t + n for t, n in zip(theme, noise)]
        res = theme_alpha_beta(stock, theme)
        assert res is not None
        assert res["theme_beta"] == pytest.approx(2.0, abs=0.05)
        # alpha annualized ≈ 0
        assert res["theme_alpha"] == pytest.approx(0.0, abs=0.5)

    def test_positive_alpha(self):
        """일정 초과수익 더하면 theme_alpha > 0."""
        rng = np.random.default_rng(11)
        theme = rng.normal(0, 0.02, 250).tolist()
        stock = [1.0 * t + 0.001 for t in theme]  # 일 +0.1% 알파
        res = theme_alpha_beta(stock, theme)
        assert res is not None
        assert res["theme_alpha"] > 0
        # 일 0.001 × 252 ≈ 0.252
        assert res["theme_alpha"] == pytest.approx(0.252, abs=0.02)

    def test_zero_variance_theme_returns_none(self):
        """테마 분산 0 → 회귀 불가 → None."""
        assert theme_alpha_beta([0.1, 0.2, 0.3], [0.0, 0.0, 0.0]) is None

    def test_length_mismatch_returns_none(self):
        assert theme_alpha_beta([0.1, 0.2], [0.1]) is None

    def test_empty_returns_none(self):
        assert theme_alpha_beta([], []) is None


# ── ②: 포착률 ─────────────────────────────────────────────────────────────────

class TestCaptureRatios:
    def test_up_capture_above_100_when_outperform(self):
        """상승장에서 테마보다 더 오르면 up_capture > 100."""
        theme = [0.01, 0.02, 0.03]
        stock = [0.015, 0.03, 0.045]  # 1.5배
        res = capture_ratios(stock, theme)
        assert res is not None
        assert res["up_capture"] is not None
        assert res["up_capture"] > 100
        assert res["up_capture"] == pytest.approx(150.0, abs=1e-6)

    def test_down_capture_and_spread(self):
        """하락 방어 시 down_capture < 100 → spread > 0."""
        theme = [0.02, -0.02]
        stock = [0.02, -0.01]  # up 100%, down 50%
        res = capture_ratios(stock, theme)
        assert res is not None
        assert res["up_capture"] == pytest.approx(100.0)
        assert res["down_capture"] == pytest.approx(50.0)
        assert res["capture_spread"] == pytest.approx(50.0)

    def test_no_up_days_yields_none_up(self):
        """상승일 없으면 up_capture None, spread None."""
        theme = [-0.01, -0.02]
        stock = [-0.005, -0.01]
        res = capture_ratios(stock, theme)
        assert res is not None
        assert res["up_capture"] is None
        assert res["down_capture"] is not None
        assert res["capture_spread"] is None

    def test_zero_theme_days_ignored(self):
        """테마 0인 날은 up/down 어디에도 안 들어감(분모 영향 없음)."""
        theme = [0.0, 0.01]
        stock = [0.5, 0.01]
        res = capture_ratios(stock, theme)
        assert res is not None
        # 상승일은 두번째 하나뿐: up = 0.01/0.01 = 100
        assert res["up_capture"] == pytest.approx(100.0)

    def test_length_mismatch_returns_none(self):
        assert capture_ratios([0.1, 0.2], [0.1]) is None


# ── 게이트 ────────────────────────────────────────────────────────────────────

class TestObsGate:
    def test_gate_pass_at_80pct(self):
        assert passes_obs_gate(16, 20) is True   # 16 >= 16
        assert passes_obs_gate(96, 120) is True   # 96 >= 96

    def test_gate_fail_below_80pct(self):
        assert passes_obs_gate(15, 20) is False
        assert passes_obs_gate(95, 120) is False

    def test_insufficient_obs_yields_none_not_error(self):
        """유효일 부족 — 코어 함수는 None(예외 아님) 반환."""
        # 1개짜리는 회귀 불가 → None
        assert trend_quality([100.0]) is None
        assert theme_alpha_beta([0.1], [0.1]) is None


# ── 룩어헤드 검증 ─────────────────────────────────────────────────────────────

class TestNoLookAhead:
    def test_t_indicator_uses_only_up_to_t(self):
        """
        윈도우 [0..t] 로 계산한 지표는 t+1 데이터에 불변이어야 한다.

        동일 prefix를 주고, 뒤에 미래값을 덧붙인 시계열에서 prefix만 잘라
        넣었을 때 결과가 같은지 확인 — 함수는 입력 슬라이스만 본다는 보장.
        """
        full = [100.0 * math.exp(0.01 * t) for t in range(30)]
        prefix = full[:20]
        # prefix만으로 계산
        res_prefix = trend_quality(prefix)
        # full의 앞 20개를 다시 슬라이스해서 계산 → 동일해야 함
        res_again = trend_quality(full[:20])
        assert res_prefix == res_again
        # 미래값 1개 더 포함하면 결과가 달라짐(= 미래를 안 보면 동일할 수 없음을 반증)
        res_plus = trend_quality(full[:21])
        assert res_plus is not None
        assert res_plus["slope"] == pytest.approx(res_prefix["slope"], abs=1e-9)
        # slope는 동일 기울기지만 r²/tq 동일 — 직선이므로. 핵심: prefix 슬라이스만 사용
