"""
MP-LV-D1 옵션 B — weight_source seam 테스트.

- MarketCapWeightSource: 가짜 시총 → 기대 weight/top5/HHI 정규화·결측 제외
- seam 선택: ACTIVE_WEIGHT_SOURCE 분기 (market_cap / holdings)
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.market_pulse.calculators import concentration as conc
from apps.market_pulse.fetchers import weight_source as ws


def _quote(cap):
    return {"marketCap": cap} if cap is not None else None


class TestMarketCapWeights:
    def test_weight_normalization(self):
        # cap 합 1000 → 정규화 weight = cap/1000
        caps = {"AAA": 500, "BBB": 300, "CCC": 200}

        class FakeClient:
            def get_quote(self, sym):
                return _quote(caps.get(sym))

        with patch.object(ws, "_sp500_symbols", return_value=list(caps)), patch(
            "packages.shared.api_request.providers.fmp.market_pulse_client.FMPClient",
            FakeClient,
        ):
            rows, meta = ws.market_cap_weights()

        by = {r.symbol: r.weight for r in rows}
        assert by["AAA"] == Decimal("0.5")
        assert by["BBB"] == Decimal("0.3")
        assert by["CCC"] == Decimal("0.2")
        # rank 정렬 (내림차순)
        assert rows[0].symbol == "AAA" and rows[0].rank == 1
        assert meta["source"] == "market_cap"
        assert meta["coverage"] == 1.0
        assert meta["n_resolved"] == 3 and meta["n_missing"] == 0

    def test_missing_symbols_excluded_and_renormalized(self):
        # CCC 결측(quote None) → 제외 후 800 기준 재정규화
        caps = {"AAA": 500, "BBB": 300, "CCC": None}

        class FakeClient:
            def get_quote(self, sym):
                return _quote(caps.get(sym))

        with patch.object(ws, "_sp500_symbols", return_value=list(caps)), patch(
            "packages.shared.api_request.providers.fmp.market_pulse_client.FMPClient",
            FakeClient,
        ):
            rows, meta = ws.market_cap_weights()

        by = {r.symbol: r.weight for r in rows}
        assert by["AAA"] == Decimal("0.625")  # 500/800
        assert by["BBB"] == Decimal("0.375")  # 300/800
        assert "CCC" not in by
        assert meta["n_resolved"] == 2 and meta["n_missing"] == 1
        assert meta["coverage"] == round(2 / 3, 4)

    def test_compute_metrics_on_market_cap_weights(self):
        # 균등 10종(각 100) → top5=0.5, top10=1.0, HHI=10*(0.1^2)=0.1
        caps = {f"T{i}": 100 for i in range(10)}

        class FakeClient:
            def get_quote(self, sym):
                return _quote(caps.get(sym))

        with patch.object(ws, "_sp500_symbols", return_value=list(caps)), patch(
            "packages.shared.api_request.providers.fmp.market_pulse_client.FMPClient",
            FakeClient,
        ):
            rows, _ = ws.market_cap_weights()
        m = conc.compute_metrics(rows)
        assert m.top5_weight == Decimal("0.5000")
        assert m.top10_weight == Decimal("1.0000")
        assert m.hhi == Decimal("0.100000")

    def test_all_missing_raises(self):
        class FakeClient:
            def get_quote(self, sym):
                return None

        with patch.object(ws, "_sp500_symbols", return_value=["AAA", "BBB"]), patch(
            "packages.shared.api_request.providers.fmp.market_pulse_client.FMPClient",
            FakeClient,
        ):
            with pytest.raises(RuntimeError):
                ws.market_cap_weights()


class TestSeamSelection:
    def test_active_universe_market_cap(self):
        with patch.object(ws, "ACTIVE_WEIGHT_SOURCE", "market_cap"):
            assert ws.active_universe() == "SP500_MCAP"

    def test_active_universe_holdings(self):
        with patch.object(ws, "ACTIVE_WEIGHT_SOURCE", "holdings"):
            assert ws.active_universe() == "SPY"

    def test_get_constituent_weights_routes_market_cap(self):
        sentinel = (["rows"], {"source": "market_cap"})
        with patch.object(ws, "ACTIVE_WEIGHT_SOURCE", "market_cap"), patch.object(
            ws, "market_cap_weights", return_value=sentinel
        ) as mc:
            out = ws.get_constituent_weights()
        assert out == sentinel and mc.called

    def test_get_constituent_weights_routes_holdings(self):
        sentinel = (["rows"], {"source": "holdings"})
        with patch.object(ws, "ACTIVE_WEIGHT_SOURCE", "holdings"), patch.object(
            ws, "holdings_weights", return_value=sentinel
        ) as hw:
            out = ws.get_constituent_weights()
        assert out == sentinel and hw.called
