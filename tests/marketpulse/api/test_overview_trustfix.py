"""HUB-V02-S1: overview A-1(_breadth_card 실데이터 우선·as_of_date) + A-2(anomaly status)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.market_pulse.api.views import overview as ov
from apps.market_pulse.models.anomaly import AnomalySignalLog
from apps.market_pulse.models.snapshot import BreadthSnapshot

pytestmark = pytest.mark.django_db


def _breadth(d, total, *, adv=0, dec=0, ad=0):
    return BreadthSnapshot.objects.create(
        date=d,
        universe="SPY",
        snapshot_time=timezone.now(),
        advance_count=adv,
        decline_count=dec,
        unchanged_count=0,
        total_count=total,
        new_high_52w=0,
        new_low_52w=0,
        ad_line=ad,
        ad_line_change=0,
    )


class TestBreadthCard:
    def test_prefers_real_over_empty_today(self):
        today = timezone.localdate()
        _breadth(today, 0)  # 오늘 빈(0) 스냅샷
        _breadth(today - timedelta(days=1), 500, adv=300, dec=200)  # 어제 실데이터
        card = ov._breadth_card()
        assert card is not None
        assert card["total"] == 500 and card["advance"] == 300
        assert card["as_of_date"] == (today - timedelta(days=1)).isoformat()

    def test_none_when_only_empty(self):
        _breadth(timezone.localdate(), 0)
        assert ov._breadth_card() is None


class TestTickerBar:
    def test_skips_empty_price_symbols(self):
        from decimal import Decimal

        from macro.models.indicators import MarketIndex, MarketIndexPrice

        real, _ = MarketIndex.objects.update_or_create(
            symbol="GCUSD",
            defaults={"name": "Gold", "category": "commodity", "sector_group": "BENCHMARK"},
        )
        MarketIndexPrice.objects.update_or_create(
            index=real, date=timezone.localdate(), defaults={"close": Decimal("100")}
        )
        gld, _ = MarketIndex.objects.update_or_create(  # 가격 0행 — 스킵돼야 함
            symbol="GLD",
            defaults={"name": "SPDR Gold", "category": "commodity", "sector_group": "BENCHMARK"},
        )
        MarketIndexPrice.objects.filter(index=gld).delete()
        syms = {r["symbol"] for r in ov._ticker_bar()}
        assert "GCUSD" in syms
        assert "GLD" not in syms


class TestAnomalyStatus:
    def _patch_ctx(self, monkeypatch, sources):
        class _C:
            pass

        c = _C()
        c.sources = sources
        monkeypatch.setattr(
            "apps.market_pulse.anomaly.engine.build_context",
            lambda *a, **k: c,
        )

    def test_no_data_when_all_inputs_missing(self, monkeypatch):
        self._patch_ctx(
            monkeypatch,
            {
                "top10_weight": "MISSING",
                "vix_change_pct": "MISSING",
                "cross_dispersion": "MISSING",
                "max_abs_sector_z": "MISSING",
            },
        )
        r = ov._anomaly_section(None)
        assert r["status"] == "no_data"
        assert r["mode"] == AnomalySignalLog.Mode.CALM
        assert "판정 불가" in r["overview"]

    def test_evaluated_calm_when_any_input_ok(self, monkeypatch):
        self._patch_ctx(
            monkeypatch,
            {
                "top10_weight": "OK",
                "vix_change_pct": "MISSING",
                "cross_dispersion": "OK",
                "max_abs_sector_z": "MISSING",
            },
        )
        r = ov._anomaly_section(None)
        assert r["status"] == "evaluated"
        assert r["mode"] == AnomalySignalLog.Mode.CALM
        assert "정상 범위" in r["overview"]

    def test_evaluated_when_fired_row_exists(self):
        AnomalySignalLog.objects.create(
            rule_id="R02",
            triggered_at=timezone.now(),
            inputs={},
            threshold={"top10_weight": 0.4},
            mode=AnomalySignalLog.Mode.HYBRID,
            headline="x",
            body="발동",
        )
        r = ov._anomaly_section(None)
        assert r["status"] == "evaluated"
        assert r["mode"] == AnomalySignalLog.Mode.HYBRID
