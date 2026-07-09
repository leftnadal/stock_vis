"""
C8 추정치 리비전 괴리 테스트 (TH-4, 설계 §2 v1.2.2 판정).

커버:
- eps_diff_at: lag 8 정상 / lag 8 결손 → 9 폴백 / 8·9 모두 결손 → None
- valid_eps_diff_count: 수집 결손(중간 구멍) → 달력 아닌 실제 diff 수
- resolve_z_mode: 25 → cross_sectional, 26 → time_series (경계)
- price_return_60d: 정상 / 결측 → None
- c8_estimate_revision 부호: EPS↑·가격정체 → 음수 / 가격급등·EPS정체 → 양수 / 반쪽 → None
- compute_c8_for_symbols: 단면 29 → 전체 None, 30 → 계산 / 가격레그 결측 → None /
  경계 26 전환 시 양 레그 동시 모드 전환 / 혼합 비율 로그
- 신시사이저 통합: C8(z_mode 포함) 통과 + z_mode 보존 + 결측 재분배
"""

from datetime import date, timedelta

import pytest

from apps.chain_sight.services import estimate_revision as er
from apps.chain_sight.services import heat_components as hc
from apps.chain_sight.services import heat_synthesis as hs

AS_OF = date(2026, 7, 10)
WK = timedelta(days=7)


def weekly_eps(as_of, n_weeks, eps_fn):
    """as_of 에서 과거로 n_weeks 개 주간(금) 스냅샷. {date: eps}. eps_fn(i)=i번째 과거."""
    return {as_of - WK * i: eps_fn(i) for i in range(n_weeks)}


def daily_prices(as_of, span_days, price_fn):
    """as_of−span..as_of 매일 종가. price_fn(offset_days_ago)."""
    return {as_of - timedelta(days=i): price_fn(i) for i in range(span_days + 1)}


# ────────────────────────────── EPS 레그 ──────────────────────────────
class TestEpsDiff:
    def test_lag8_primary(self):
        eps = {AS_OF: 6.0, AS_OF - timedelta(days=56): 5.0}  # lag 8
        assert er.eps_diff_at(eps, AS_OF) == pytest.approx(1.0)

    def test_lag9_fallback_when_lag8_absent(self):
        eps = {AS_OF: 6.0, AS_OF - timedelta(days=63): 5.5}  # lag 8 부재 → lag 9
        assert er.eps_diff_at(eps, AS_OF) == pytest.approx(0.5)

    def test_none_when_both_lags_absent(self):
        eps = {AS_OF: 6.0, AS_OF - timedelta(days=70): 5.0}  # 8·9 모두 부재
        assert er.eps_diff_at(eps, AS_OF) is None

    def test_none_when_anchor_absent(self):
        assert er.eps_diff_at({AS_OF - timedelta(days=56): 5.0}, AS_OF) is None

    def test_count_follows_actual_diffs_not_calendar(self):
        """중간 3주 구멍 → 그 주변 diff 미성립 → 카운트가 달력보다 작다."""
        eps = weekly_eps(AS_OF, 20, lambda i: 5.0 + i * 0.1)
        full_count = er.valid_eps_diff_count(eps, AS_OF)
        # 중간 3주(i=5,6,7) 제거 → 그 날짜의 diff + 그들을 파트너로 쓰는 날짜 diff 소멸
        holed = {d: v for j, (d, v) in enumerate(sorted(eps.items(), reverse=True))
                 if j not in (5, 6, 7)}
        holed_count = er.valid_eps_diff_count(holed, AS_OF)
        assert holed_count < full_count  # 달력이 아니라 실제 diff 수를 따른다


# ────────────────────────────── z_mode 경계 ──────────────────────────────
class TestZMode:
    def test_25_cross_sectional(self):
        assert er.resolve_z_mode(25) == "cross_sectional"

    def test_26_time_series(self):
        assert er.resolve_z_mode(26) == "time_series"

    def test_threshold_is_single_constant(self):
        assert er.Z_MODE_TS_THRESHOLD == 26


# ────────────────────────────── 가격 레그 ──────────────────────────────
class TestPriceLeg:
    def test_return_60d(self):
        px = {AS_OF: 110.0, AS_OF - timedelta(days=60): 100.0}
        assert er.price_return_60d(px, AS_OF) == pytest.approx(0.10)

    def test_none_when_missing(self):
        assert er.price_return_60d({AS_OF: 110.0}, AS_OF) is None  # 시작가 결측

    def test_nearest_trading_day_tolerance(self):
        px = {AS_OF - timedelta(days=1): 110.0, AS_OF - timedelta(days=61): 100.0}
        assert er.price_return_60d(px, AS_OF) == pytest.approx(0.10)  # ±tol 근사


# ────────────────────────────── 부호 방향 (순수 조립기) ──────────────────────────────
class TestC8Sign:
    def test_eps_up_price_flat_negative(self):
        """EPS 상향·가격 정체 → C8 음수 (이익이 과열을 식힘)."""
        comp = hc.c8_estimate_revision(z_price=0.0, z_eps=2.0, z_mode="cross_sectional")
        assert comp["z"] == pytest.approx(-2.0) and comp["z"] < 0

    def test_price_surge_eps_flat_positive(self):
        """가격 급등·EPS 정체 → C8 양수 (멀티플 단독 팽창 = 과열)."""
        comp = hc.c8_estimate_revision(z_price=2.0, z_eps=0.0, z_mode="cross_sectional")
        assert comp["z"] == pytest.approx(2.0) and comp["z"] > 0
        assert comp["s"] == pytest.approx(hc.sigmoid(2.0))

    def test_half_leg_none_gives_none(self):
        """반쪽(한 레그 z None) → C8 None (반쪽 계산 금지)."""
        comp = hc.c8_estimate_revision(z_price=2.0, z_eps=None)
        assert comp["z"] is None and comp["z_mode"] is None
        assert comp["missing_reason"] == "c8_z_unavailable"


# ────────────────────────────── 오케스트레이션 (단면/모드) ──────────────────────────────
def _cold_start_symbol(i):
    """count<26(cross_sectional) 종목: 스냅샷 2개(diff 1) + 가격 2개. i로 값 분산."""
    eps = {AS_OF: 5.0 + i * 0.2, AS_OF - timedelta(days=56): 5.0}
    px = {AS_OF: 100.0 + i, AS_OF - timedelta(days=60): 100.0}
    return {"eps_by_date": eps, "price_by_date": px}


@pytest.mark.django_db  # (DB 미사용이나 다른 테스트와 픽스처 정합)
class TestOrchestration:
    def test_thin_cross_section_29_all_none(self):
        series = {f"S{i}": _cold_start_symbol(i) for i in range(29)}
        comps, mix = er.compute_c8_for_symbols(series, AS_OF)
        assert all(c["z"] is None for c in comps.values())
        assert all(c["missing_reason"] == "c8_thin_cross_section" for c in comps.values())
        assert mix == {"ts": 0, "cs": 0, "none": 29}

    def test_cross_section_30_computes(self):
        series = {f"S{i}": _cold_start_symbol(i) for i in range(30)}
        comps, mix = er.compute_c8_for_symbols(series, AS_OF)
        computed = [c for c in comps.values() if c["z"] is not None]
        assert len(computed) == 30
        assert all(c["z_mode"] == "cross_sectional" for c in computed)
        assert mix["cs"] == 30 and mix["none"] == 0

    def test_price_leg_missing_gives_none(self):
        """가격 레그 결측 → C8 None (EPS 레그 정상이어도)."""
        series = {f"S{i}": _cold_start_symbol(i) for i in range(30)}
        series["S0"]["price_by_date"] = {AS_OF: 100.0}  # 시작가 결측 → px_ret None
        comps, mix = er.compute_c8_for_symbols(series, AS_OF)
        assert comps["S0"]["z"] is None
        assert comps["S0"]["missing_reason"] == "c8_leg_missing"

    def test_boundary_26_both_legs_switch_to_time_series(self):
        """count 26 종목 → 양 레그 동시 time_series (혼합 모드 부재)."""
        # 34주 스냅샷 → 유효 diff 26개 → time_series
        eps = weekly_eps(AS_OF, 34, lambda i: 5.0 + (34 - i) * 0.05)
        px = daily_prices(AS_OF, 34 * 7 + 60, lambda d: 100.0 + (34 * 7 + 60 - d) * 0.05)
        ts_sym = {"eps_by_date": eps, "price_by_date": px}
        assert er.valid_eps_diff_count(eps, AS_OF) == 26  # 경계
        # 단면 채우기용 cold-start 30종목 + ts 종목 1
        series = {f"S{i}": _cold_start_symbol(i) for i in range(30)}
        series["TS"] = ts_sym
        comps, mix = er.compute_c8_for_symbols(series, AS_OF)
        assert comps["TS"]["z_mode"] == "time_series"  # 양 레그 공동 ts
        assert comps["TS"]["z"] is not None
        assert mix["ts"] == 1 and mix["cs"] == 30


@pytest.mark.django_db
class TestC8FromDB:
    def test_empty_universe(self):
        comps, mix = er.compute_c8_from_db([], AS_OF)
        assert comps == {} and mix == {"ts": 0, "cs": 0, "none": 0}

    def test_cold_start_no_snapshots_all_none(self):
        """스냅샷 0(콜드 스타트) → 전종목 leg_missing (정상)."""
        comps, mix = er.compute_c8_from_db(["AAPL", "MSFT"], AS_OF)
        assert all(c["z"] is None for c in comps.values())
        assert mix["none"] == 2 and mix["ts"] == 0 and mix["cs"] == 0


# ────────────────────────────── 신시사이저 통합 ──────────────────────────────
class TestSynthesizerIntegration:
    def _base_components(self):
        """C1~C7 유효(z=0.5) 성분."""
        return {k: {"z": 0.5, "raw": None, "missing_reason": None}
                for k in ("C1", "C2", "C3", "C4", "C5", "C6", "C7")}

    def test_c8_present_zmode_preserved(self):
        comps = self._base_components()
        comps["C8"] = hc.c8_estimate_revision(z_price=1.0, z_eps=0.2, z_mode="time_series")
        out = hs.synthesize_heat(comps)
        assert out["status"] != "not_computed"
        assert out["components"]["C8"]["z_mode"] == "time_series"  # 보존
        assert out["components"]["C8"]["z"] == pytest.approx(0.8)

    def test_c8_none_redistributes(self):
        """C8=None → 기존 결측 재분배(neutral 아님). 결측 1개라 산출됨."""
        comps = self._base_components()
        comps["C8"] = hc.c8_estimate_revision(z_price=None, z_eps=None)
        out = hs.synthesize_heat(comps)
        assert out["status"] != "not_computed"  # 결측 1 < 3 → 재분배 후 산출
        assert out["components"]["C8"]["z"] is None
        assert out["missing_count"] == 1
