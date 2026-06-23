"""
MP1-test-gap (P1-close) — fmp_weights.fetch_holdings 파싱/정규화 테스트.

소속: tests/marketpulse/fetchers (PR-B fetcher 테스트 모듈 갭 보강).
대상: apps/market_pulse/fetchers/fmp_weights.py
  - fetch_holdings: raw FMP payload → HoldingRow 정렬·정규화·rank 부여
  - _request_etf_holder: API_KEY 미설정 / payload 타입 가드
방식: _request_etf_holder를 patch(외부 API·CB 무네트워크). 행위 단언만(로직 무변경).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.market_pulse.fetchers import fmp_weights as fw


def _holdings(*items):
    """raw FMP etf/holdings payload (dict 리스트) 생성 헬퍼."""
    return list(items)


class TestFetchHoldingsParsing:
    def test_weight_pct_to_decimal_and_rank_sort(self):
        raw = _holdings(
            {"symbol": "BBB", "name": "Beta", "weightPercentage": 30, "sharesNumber": 10},
            {"symbol": "AAA", "name": "Alpha", "weightPercentage": 50, "sharesNumber": 20},
            {"symbol": "CCC", "name": "Gamma", "weightPercentage": 20, "sharesNumber": 5},
        )
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("spy")

        # weightPercentage / 100 = Decimal weight
        by = {r.symbol: r.weight for r in rows}
        assert by["AAA"] == Decimal("0.5")
        assert by["BBB"] == Decimal("0.3")
        assert by["CCC"] == Decimal("0.2")
        # 내림차순 정렬 + rank 1부터
        assert [r.symbol for r in rows] == ["AAA", "BBB", "CCC"]
        assert [r.rank for r in rows] == [1, 2, 3]

    def test_asset_key_takes_priority_over_symbol(self):
        # FMP payload는 'asset' 키 우선 (symbol fallback)
        raw = _holdings({"asset": "MSFT", "symbol": "IGNORED", "weightPercentage": 10})
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("SPY")
        assert rows[0].symbol == "MSFT"

    def test_symbol_uppercased(self):
        raw = _holdings({"symbol": "aapl", "weightPercentage": 5})
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("spy")
        assert rows[0].symbol == "AAPL"

    def test_shares_int_coercion_and_none(self):
        raw = _holdings(
            {"symbol": "AAA", "weightPercentage": 60, "sharesNumber": "123"},
            {"symbol": "BBB", "weightPercentage": 40},  # sharesNumber 부재
        )
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("SPY")
        by = {r.symbol: r.shares for r in rows}
        assert by["AAA"] == 123
        assert by["BBB"] is None

    def test_name_truncated_to_200(self):
        raw = _holdings({"symbol": "AAA", "name": "X" * 500, "weightPercentage": 100})
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("SPY")
        assert len(rows[0].name) == 200


class TestFetchHoldingsSkips:
    def test_empty_symbol_skipped(self):
        raw = _holdings(
            {"symbol": "", "weightPercentage": 50},
            {"asset": None, "weightPercentage": 30},
            {"symbol": "AAA", "weightPercentage": 20},
        )
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("SPY")
        assert [r.symbol for r in rows] == ["AAA"]

    def test_none_weight_skipped(self):
        raw = _holdings(
            {"symbol": "AAA", "weightPercentage": None},
            {"symbol": "BBB", "weightPercentage": 10},
        )
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("SPY")
        assert [r.symbol for r in rows] == ["BBB"]

    def test_non_numeric_weight_skipped(self):
        raw = _holdings(
            {"symbol": "AAA", "weightPercentage": "n/a"},
            {"symbol": "BBB", "weightPercentage": 10},
        )
        with patch.object(fw, "_request_etf_holder", return_value=raw):
            rows = fw.fetch_holdings("SPY")
        assert [r.symbol for r in rows] == ["BBB"]

    def test_empty_payload_returns_empty(self):
        with patch.object(fw, "_request_etf_holder", return_value=[]):
            rows = fw.fetch_holdings("SPY")
        assert rows == []


class TestRequestEtfHolderGuards:
    def test_missing_api_key_raises(self, settings):
        settings.FMP_API_KEY = None
        with pytest.raises(RuntimeError, match="FMP_API_KEY"):
            fw._request_etf_holder("SPY")

    def test_non_list_payload_raises(self, settings):
        settings.FMP_API_KEY = "dummy"

        class FakeResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"error": "premium"}  # list 아님

        with patch.object(fw.requests, "get", return_value=FakeResp()):
            with pytest.raises(ValueError, match="payload type"):
                fw._request_etf_holder("SPY")
