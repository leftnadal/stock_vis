"""MPS-1 MP-STRESS — 연속 스트레스 스코어 엔진 순수 함수 (결정론 코어).

계약(D-MPS-SCORE / D-MPS-DIRECTION / D-MPS-COPY):
  - 종합 스코어 = 14지표 z의 가족 균등가중(1/|fam|) z 평균 = 4 유효 축(analog 철학) 균등평균.
  - 카테고리 서브스코어(표시축) + 카테고리별 Δ5d.
  - 백분위 = 당일 스코어의 자기 역사 내 백분위(≤ 비율).
  - 방향 2종: 스트레스 Δ5d·Δ20d 부호 / 가격 SPY vs MA20·MA60.
  - level_band 잠정 경계(S4-REBASE 재산정 대상).
  - 성분 동결: 신규 3종(DTWEXBGS·STLFSI4·SOFR)은 스코어 미편입(수집만).
"""

from __future__ import annotations

import pytest

from apps.market_pulse.regime import stress
from apps.market_pulse.regime.inputs import ALL_INPUT_KEYS, INDICATOR_CODE_MAP

pytestmark = [pytest.mark.unit]


# ── 성분 동결 (Step 1.3 / Part2 검증) ──────────────────────────────────
class TestComponentFreeze:
    def test_score_keys_are_14_full_vector(self):
        assert stress.STRESS_SCORE_KEYS == ALL_INPUT_KEYS
        assert len(stress.STRESS_SCORE_KEYS) == 14

    def test_new_series_not_in_score_keys(self):
        # 신규 수집 3종은 스코어 성분에 없어야(수집만·미편입, S4-REBASE 편입 심사 전).
        for code in ("DTWEXBGS", "STLFSI4", "SOFR"):
            assert code not in stress.STRESS_SCORE_KEYS

    def test_new_series_not_loaded_into_inputs(self):
        # 구조적 보장: 신규 series는 INDICATOR_CODE_MAP(=load_inputs 대상)에 없음
        #   → 벡터/baseline/스코어 어디에도 진입 불가.
        loaded_codes = set(INDICATOR_CODE_MAP.values())
        for code in ("DTWEXBGS", "STLFSI4", "SOFR"):
            assert code not in loaded_codes


# ── 종합 스코어 (D-MPS-SCORE) ──────────────────────────────────────────
class TestCompositeScore:
    def _full_z(self):
        # stress(3) 평균 1.0, financial(9) 평균 1.0, 단독 0.5 / 1.5
        return {
            "drawdown_pct": -1.0, "vix": 2.0, "vix3m": 2.0,       # 평균 1.0
            "nfci": 1.0, "nfci_credit": 1.0, "nfci_leverage": 1.0,
            "nfci_risk": 1.0, "hy_oas_pct": 1.0, "hy_ccc_oas_pct": 1.0,
            "t10y2y_pct": 1.0, "t10y3m_pct": 1.0, "move": 1.0,    # 평균 1.0
            "return_1d_pct": 0.5, "vol_20d_pct": 1.5,
        }

    def test_axis_scores_family_mean(self):
        axes = stress.axis_scores(self._full_z())
        assert axes["stress"] == pytest.approx(1.0)
        assert axes["financial"] == pytest.approx(1.0)
        assert axes["return_1d_pct"] == pytest.approx(0.5)
        assert axes["vol_20d_pct"] == pytest.approx(1.5)

    def test_composite_is_axis_mean(self):
        # mean(1.0, 1.0, 0.5, 1.5) = 1.0
        assert stress.composite_score(self._full_z()) == pytest.approx(1.0)

    def test_missing_member_uses_present_only(self):
        z = self._full_z()
        del z["vix3m"]  # stress 가족 = mean(-1.0, 2.0) = 0.5
        axes = stress.axis_scores(z)
        assert axes["stress"] == pytest.approx(0.5)
        # composite = mean(0.5, 1.0, 0.5, 1.5) = 0.875
        assert stress.composite_score(z) == pytest.approx(0.875)

    def test_missing_whole_axis_excluded(self):
        z = self._full_z()
        del z["return_1d_pct"]  # 축 return_1d_pct 소멸 → 3축 평균
        axes = stress.axis_scores(z)
        assert axes["return_1d_pct"] is None
        # composite = mean(1.0, 1.0, 1.5) = 1.166..→ round 3
        assert stress.composite_score(z) == pytest.approx(1.167)

    def test_empty_z_returns_none(self):
        assert stress.composite_score({}) is None
        assert stress.axis_scores({}) == {
            "stress": None, "financial": None,
            "return_1d_pct": None, "vol_20d_pct": None,
        }


# ── 카테고리 서브스코어 (D-MPS-SCORE 표시축) ───────────────────────────
class TestCategorySubscores:
    def test_categories_cover_all_14_keys(self):
        covered = [k for members in stress.STRESS_CATEGORIES.values() for k in members]
        assert sorted(covered) == sorted(ALL_INPUT_KEYS)
        # 표시 카테고리는 상호배타(중복 성분 없음)
        assert len(covered) == len(set(covered)) == 14

    def test_category_z_mean_and_d5(self):
        today = {"vix": 2.0, "vix3m": 4.0, "move": 0.0}  # volatility 평균 2.0
        prior = {"vix": 1.0, "vix3m": 1.0, "move": 1.0}  # volatility 평균 1.0
        cats = {c["key"]: c for c in stress.category_subscores(today, prior)}
        assert cats["volatility"]["z"] == pytest.approx(2.0)
        assert cats["volatility"]["d5"] == pytest.approx(1.0)  # 2.0 − 1.0

    def test_category_d5_none_without_prior(self):
        cats = {c["key"]: c for c in stress.category_subscores({"vix": 2.0}, None)}
        assert cats["volatility"]["d5"] is None


# ── 백분위 (D-MPS-COPY) ────────────────────────────────────────────────
class TestPercentile:
    def test_median_is_50th(self):
        pop = [0.0, 1.0, 2.0, 3.0, 4.0]
        # score=2.0 → ≤ 3개(0,1,2)/5 = 60%
        assert stress.percentile_of(2.0, pop) == pytest.approx(60.0)

    def test_top_is_100(self):
        assert stress.percentile_of(4.0, [0.0, 1.0, 2.0, 3.0, 4.0]) == pytest.approx(100.0)

    def test_empty_population_none(self):
        assert stress.percentile_of(1.0, []) is None


# ── 방향 2종 (D-MPS-DIRECTION) ────────────────────────────────────────
class TestStressDirection:
    def test_both_up_worsening(self):
        d = stress.stress_direction(1.5, 1.0, 0.5)  # today, t-5, t-20
        assert d["d5"] == pytest.approx(0.5)
        assert d["d20"] == pytest.approx(1.0)
        assert d["state"] == "worsening"

    def test_both_down_easing(self):
        d = stress.stress_direction(0.5, 1.0, 1.5)
        assert d["state"] == "easing"

    def test_mixed(self):
        d = stress.stress_direction(1.0, 0.5, 1.5)  # d5>0, d20<0
        assert d["state"] == "mixed"

    def test_none_when_history_missing(self):
        d = stress.stress_direction(1.0, None, 0.5)
        assert d["d5"] is None
        assert d["state"] is None


class TestPriceTrend:
    def test_above_both_uptrend(self):
        t = stress.price_trend(100.0, 95.0, 90.0)
        assert t["vs_ma20"] == "above"
        assert t["vs_ma60"] == "above"
        assert t["state"] == "uptrend"

    def test_below_both_downtrend(self):
        t = stress.price_trend(85.0, 95.0, 90.0)
        assert t["state"] == "downtrend"

    def test_mixed(self):
        t = stress.price_trend(92.0, 95.0, 90.0)  # below ma20, above ma60
        assert t["state"] == "mixed"

    def test_none_when_ma_missing(self):
        t = stress.price_trend(100.0, None, 90.0)
        assert t["vs_ma20"] is None
        assert t["state"] is None


# ── level_band 잠정 경계 (S4-REBASE 재산정 대상) ──────────────────────
class TestLevelBand:
    def test_stable_below_low(self):
        assert stress.level_band(0.4) == "stable"

    def test_caution_mid(self):
        assert stress.level_band(1.0) == "caution"

    def test_severe_high(self):
        assert stress.level_band(1.6) == "severe"

    def test_boundaries_inclusive_lower(self):
        # 경계값은 상위 밴드에 포함(≥)
        assert stress.level_band(0.5) == "caution"
        assert stress.level_band(1.5) == "severe"

    def test_band_vocab_excludes_crisis(self):
        # 금지규칙 2(D-MPS-COPY): 밴드 enum에 classifier "crisis" 단어를 두지 않는다.
        #   FE가 raw 값을 표시해도 규칙 위반이 시작되지 않도록 코드로 고정(MPS-2 FE 짝).
        bands = {
            stress.level_band(s)
            for s in (-1.0, 0.0, 0.4, 0.5, 1.0, 1.49, 1.5, 1.6, 3.0)
        }
        assert bands == {"stable", "caution", "severe"}
        assert "crisis" not in bands

    def test_none_score(self):
        assert stress.level_band(None) is None
