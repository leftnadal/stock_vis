"""
C4 콜드스타트 게이트 + C6/C7 배선 테스트 (TH-8, 결정13=C) — 설계 앵커 §2 · §3-1.

커버:
- C4 게이트 3분기: diff<26 결측 / 26≤diff<60 확장 z_mode / ≥60 정식 z_mode / primary 부재
- C4 확장→정식 이음새: 창 전환 z 연속성(급점프 없음)
- C7: no_symbols / no_data / 3년 커버 미달 insufficient / 정상 z(3년 fixture)
- C6: no_pairs / 커버 미달 insufficient / 정상 z
- 조립기: _NOT_WIRED=(C1,C3) / C4·C6·C7 comp 편입 + missing 산술
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.chain_sight.models import EtfSnapshot, HeatEntity
from apps.chain_sight.services import heat_beat as hb
from apps.chain_sight.services.c4_flow_service import c4_etf_flow_from_db
from apps.chain_sight.services.c6c7_service import (
    c6_correlation_from_db,
    c7_dollar_volume_from_db,
)

S0 = date(2026, 1, 1)


def _mk_snapshots(sym, n, shares_fn, nav=50):
    EtfSnapshot.objects.bulk_create([
        EtfSnapshot(symbol=sym, snapshot_date=S0 + timedelta(days=i),
                    shares_outstanding=shares_fn(i), nav=Decimal(str(nav)))
        for i in range(n)
    ])


# ────────────────────────────── C4 게이트 ──────────────────────────────
@pytest.mark.django_db
class TestC4Gate:
    def test_no_primary(self):
        c = c4_etf_flow_from_db([], S0)
        assert c["missing_reason"] == "c4_no_primary_etf" and c["z_mode"] is None

    def test_insufficient_below_26(self):
        _mk_snapshots("XLK", 10, lambda i: 1_000_000 + i * 1000)  # diff 9 < 26
        c = c4_etf_flow_from_db(["XLK"], S0 + timedelta(days=9))
        assert c["missing_reason"] == "c4_insufficient_history" and c["z_mode"] is None

    def test_expanding_26_to_60(self):
        _mk_snapshots("XLK", 40, lambda i: 1_000_000 + i * 1000 + (i % 3) * 500)  # diff 39
        c = c4_etf_flow_from_db(["XLK"], S0 + timedelta(days=39))
        assert c["z_mode"] == "time_series_expanding" and c["z"] is not None

    def test_full_above_60(self):
        _mk_snapshots("XLK", 70, lambda i: 1_000_000 + i * 1000 + (i % 3) * 500)  # diff 69
        c = c4_etf_flow_from_db(["XLK"], S0 + timedelta(days=69))
        assert c["z_mode"] == "time_series" and c["z"] is not None

    def test_seam_continuity_expanding_to_full(self):
        # 같은 시계열에서 diff=59(확장) → diff=61(정식) 전환 시 z 급점프 없음.
        _mk_snapshots("XLK", 72, lambda i: 1_000_000 + i * 1000 + (i % 5) * 300)
        c59 = c4_etf_flow_from_db(["XLK"], S0 + timedelta(days=59))
        c61 = c4_etf_flow_from_db(["XLK"], S0 + timedelta(days=61))
        assert c59["z_mode"] == "time_series_expanding"
        assert c61["z_mode"] == "time_series"
        assert abs(c59["z"] - c61["z"]) < 1.0  # 창 확장→정식 연속성


# ────────────────────────────── C6/C7 fixture ──────────────────────────────
def _mk_prices(sym, n, close_fn, vol_fn, start):
    from packages.shared.stocks.models import DailyPrice, Stock

    st, _ = Stock.objects.get_or_create(symbol=sym)
    DailyPrice.objects.bulk_create([
        DailyPrice(stock=st, currency="USD", date=start + timedelta(days=i),
                   open_price=Decimal(str(close_fn(i))), high_price=Decimal(str(close_fn(i))),
                   low_price=Decimal(str(close_fn(i))), close_price=Decimal(str(close_fn(i))),
                   volume=vol_fn(i))
        for i in range(n)
    ])


@pytest.mark.django_db
class TestC7DollarVolume:
    def test_no_symbols(self):
        assert c7_dollar_volume_from_db([], S0)["missing_reason"] == "c7_no_symbols"

    def test_no_data(self):
        assert c7_dollar_volume_from_db(["ZZZ"], S0)["missing_reason"] == "c7_no_data"

    def test_insufficient_coverage(self):
        # 30일치만 → 3년 커버 미달
        _mk_prices("AAA", 30, lambda i: 100, lambda i: 1000, S0)
        c = c7_dollar_volume_from_db(["AAA"], S0 + timedelta(days=29))
        assert c["missing_reason"] == "c7_insufficient_history"

    def test_normal_z(self):
        # 작은 파라미터로 3년 커버 충족 fixture
        start = date(2023, 1, 1)
        as_of = date(2023, 3, 1)  # 59일 후
        _mk_prices("AAA", 60, lambda i: 100, lambda i: 1000 + i * 10, start)
        c = c7_dollar_volume_from_db(
            ["AAA"], as_of, lookback_days=40, window=5, step_days=5, min_n=3,
        )
        assert c["missing_reason"] is None and c["z"] is not None


@pytest.mark.django_db
class TestC6Correlation:
    def test_no_pairs(self):
        assert c6_correlation_from_db(["AAA"], S0)["missing_reason"] == "c6_no_pairs"

    def test_insufficient_coverage(self):
        _mk_prices("AAA", 30, lambda i: 100 + i, lambda i: 1000, S0)
        _mk_prices("BBB", 30, lambda i: 100 + i, lambda i: 1000, S0)
        c = c6_correlation_from_db(["AAA", "BBB"], S0 + timedelta(days=29))
        assert c["missing_reason"] == "c6_insufficient_history"

    def test_normal_z(self):
        start = date(2023, 1, 1)
        as_of = date(2023, 3, 1)
        # 두 종목 상관 있는 가격(공행) — 변동
        _mk_prices("AAA", 60, lambda i: 100 + (i % 7) * 2, lambda i: 1000, start)
        _mk_prices("BBB", 60, lambda i: 50 + (i % 7) * 1.5, lambda i: 1000, start)
        c = c6_correlation_from_db(
            ["AAA", "BBB"], as_of, lookback_days=40, corr_window=5, step_days=5, min_n=3,
        )
        assert c["missing_reason"] is None and c["z"] is not None


# ────────────────────────────── 조립기 편입 ──────────────────────────────
@pytest.mark.django_db
class TestAssemblyWiring:
    def test_c4_c6_c7_wired_not_in_not_wired(self):
        # TH-10 에서 C1/C3 도 배선되어 _NOT_WIRED 는 빈 튜플. C4/C6/C7 은 배선됨.
        for k in ("C4", "C6", "C7"):
            assert k not in hb._NOT_WIRED

    def test_c4_c6_c7_in_components(self):
        e = HeatEntity.objects.get(kind="sector", ref_id="Basic Materials")
        comp = hb._real_sector_components(e, [], date(2026, 7, 9), {})
        # C4/C6/C7 이 comp 에 존재(배선됨) — 데이터 게이트로 결측이어도 키는 존재
        for k in ("C4", "C6", "C7"):
            assert k in comp
        assert comp["C4"]["missing_reason"] == "c4_insufficient_history"
        assert comp["C6"]["missing_reason"] in ("c6_no_pairs", "c6_no_data", "c6_insufficient_history")

    def test_status_transition_when_missing_below_limit(self):
        # 6 성분 present + 2 결측(C4 게이트·C8 주간) → missing 2 < MISSING_LIMIT(3) → computed.
        from apps.chain_sight.services.heat_components import make_component
        from apps.chain_sight.services.heat_synthesis import synthesize_heat

        comp = {k: make_component(0.5, raw=1) for k in ("C1", "C2", "C3", "C5", "C6", "C7")}
        comp["C4"] = make_component(None, missing_reason="c4_insufficient_history")
        comp["C8"] = make_component(None, missing_reason="c8_no_sector_data")
        synth = synthesize_heat(comp)
        assert synth["status"] != "not_computed" and synth["score"] is not None
