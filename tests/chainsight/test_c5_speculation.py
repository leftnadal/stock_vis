"""
C5 투기 심리 배선 테스트 (TH-7d, 결정12b) — 설계 앵커 §2 C5 · §6.4 · §3-5.

커버:
- 레버리지 9종 시드(0021): active leveraged 9 · ERX 승격 · XLB/XLC 미시드 · measured_liquidity · 멱등
- 백필 가드(빈 응답 skip)·멱등·개별 bar 필드 가드
- c5_speculation_from_db: 레버리지 부재 결측 / 비율 z 정방향(레버리지 비율↑ → z↑)
- 조립기: _NOT_WIRED 에 C5 없음 / 정상 섹터 C5 present / XLB·XLC C5 결측
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.chain_sight.models import EtfDailyBar, HeatEntity, ThemeEtfMap
from apps.chain_sight.services import c5_speculation_service as c5s
from apps.chain_sight.services import heat_beat as hb
from apps.chain_sight.services import heat_components as hc

AS_OF = date(2026, 7, 9)


# ────────────────────────────── 레버리지 시드 (0021) ──────────────────────────────
@pytest.mark.django_db
class TestLeveragedSeed:
    def test_9_active_leveraged(self):
        assert ThemeEtfMap.objects.filter(active=True, role="leveraged").count() == 9

    def test_erx_promoted(self):
        erx = ThemeEtfMap.objects.get(etf_symbol="ERX", role="leveraged")
        assert erx.active is True and erx.leverage_factor == 2
        assert erx.measured_liquidity_usd == Decimal("30900000")

    def test_xlb_xlc_no_leveraged(self):
        for ref in ["Basic Materials", "Communication Services"]:
            e = HeatEntity.objects.get(kind="sector", ref_id=ref)
            assert not ThemeEtfMap.objects.filter(
                theme=e, role="leveraged", active=True
            ).exists()

    def test_measured_liquidity_recorded(self):
        assert ThemeEtfMap.objects.get(etf_symbol="TECL").measured_liquidity_usd == Decimal(
            "218300000"
        )

    def test_seed_idempotent(self):
        before = ThemeEtfMap.objects.count()
        e = HeatEntity.objects.get(kind="sector", ref_id="Technology")
        ThemeEtfMap.objects.update_or_create(
            theme=e, etf_symbol="TECL", role="leveraged",
            defaults={"leverage_factor": 3, "active": True,
                      "measured_liquidity_usd": 218_300_000},
        )
        assert ThemeEtfMap.objects.count() == before


# ────────────────────────────── 백필 ──────────────────────────────
@pytest.mark.django_db
class TestC5Backfill:
    def test_guard_empty_skips_no_db(self):
        c = MagicMock()
        c.get_historical_price.return_value = []
        r = c5s.backfill_etf_daily_bars(c, ["XLK"], date(2026, 1, 1), date(2026, 2, 1))
        assert r["skipped_syms"] == 1 and r["created"] == 0
        assert EtfDailyBar.objects.count() == 0

    def test_idempotent(self):
        bars = [{"date": "2026-05-01", "close": 10, "volume": 1000},
                {"date": "2026-05-02", "close": 11, "volume": 2000}]
        c = MagicMock()
        c.get_historical_price.return_value = bars
        c5s.backfill_etf_daily_bars(c, ["XLK"], date(2026, 5, 1), date(2026, 5, 2))
        r2 = c5s.backfill_etf_daily_bars(c, ["XLK"], date(2026, 5, 1), date(2026, 5, 2))
        assert r2["created"] == 0 and r2["updated"] == 2
        assert EtfDailyBar.objects.filter(symbol="XLK").count() == 2

    def test_field_guard_skips_bar(self):
        bars = [{"date": "2026-05-01", "volume": None}, {"date": None, "volume": 100}]
        c = MagicMock()
        c.get_historical_price.return_value = bars
        r = c5s.backfill_etf_daily_bars(c, ["XLK"], date(2026, 5, 1), date(2026, 5, 2))
        assert r["skipped_bars"] == 2 and r["created"] == 0


# ────────────────────────────── from_db 계산 ──────────────────────────────
def _mk_bars(symbol, n, vol_fn, start):
    EtfDailyBar.objects.bulk_create([
        EtfDailyBar(symbol=symbol, date=start + timedelta(days=i), close=Decimal("10"),
                    volume=vol_fn(i))
        for i in range(n)
    ])


@pytest.mark.django_db
class TestC5FromDb:
    def test_no_leveraged_missing(self):
        c = c5s.c5_speculation_from_db(["XLB"], [], AS_OF)
        assert c["missing_reason"] == "c5_no_leveraged_etf"

    def test_no_volume_data_missing(self):
        c = c5s.c5_speculation_from_db(["XLK"], ["TECL"], AS_OF)
        assert c["missing_reason"] == "c5_no_volume_data"

    def test_ratio_z_positive_when_leverage_surges(self):
        # 원본 vol 일정(1000). 레버리지 vol = 과거 변동(100+i*5, 비율 0.1~0.3) → 최근 5일 900.
        # current 비율(0.9)↑ → z 양수(정방향). 과거 변동으로 std>0 확보.
        n = 50
        start = AS_OF - timedelta(days=n - 1)
        _mk_bars("XLK", n, lambda i: 1000, start)
        _mk_bars("TECL", n, lambda i: 900 if i >= n - 5 else 100 + i * 5, start)
        c = c5s.c5_speculation_from_db(
            ["XLK"], ["TECL"], AS_OF,
            lookback_days=40, window=5, step_days=5, min_n=3,
        )
        assert c["missing_reason"] is None
        assert c["z"] is not None and c["z"] > 0  # 레버리지 급등 = 과열 상승 정방향
        assert c["raw"] == pytest.approx(0.9)  # 최근 window 비율


# ────────────────────────────── 조립기 배선 ──────────────────────────────
@pytest.mark.django_db
class TestC5Assembly:
    def test_c5_not_in_not_wired(self):
        assert "C5" not in hb._NOT_WIRED

    def test_xlb_c5_missing_in_assembly(self):
        e = HeatEntity.objects.get(kind="sector", ref_id="Basic Materials")
        comp = hb._real_sector_components(e, [], AS_OF, {})
        assert comp["C5"]["missing_reason"] == "c5_no_leveraged_etf"

    def test_normal_sector_c5_present(self, monkeypatch):
        e = HeatEntity.objects.get(kind="sector", ref_id="Technology")
        monkeypatch.setattr(
            c5s, "c5_speculation_from_db",
            lambda pri, lev, as_of: hc.make_component(1.5, raw=0.9),
        )
        comp = hb._real_sector_components(e, [], AS_OF, {})
        assert comp["C5"]["z"] == 1.5 and comp["C5"]["missing_reason"] is None
