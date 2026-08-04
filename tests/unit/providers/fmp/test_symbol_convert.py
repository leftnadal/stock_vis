"""
FMP 심볼 변환 순수 함수 테스트 (DOTSYM Slice 1).

계약: 내부 정본(dot) ↔ FMP API(hyphen). passthrough 행위보존.
"""

import pytest

from packages.shared.api_request.providers.fmp.symbol_convert import (
    from_fmp_symbol,
    restore_symbols_in_response,
    to_fmp_symbol,
    to_fmp_symbols_param,
)


class TestToFmpSymbol:
    @pytest.mark.parametrize(
        "internal,fmp",
        [
            ("BRK.B", "BRK-B"),
            ("BF.B", "BF-B"),
            ("AAPL", "AAPL"),   # passthrough (dot 없음)
            ("MSFT", "MSFT"),
        ],
    )
    def test_dot_to_hyphen(self, internal, fmp):
        assert to_fmp_symbol(internal) == fmp

    def test_none_and_empty_passthrough(self):
        assert to_fmp_symbol(None) is None
        assert to_fmp_symbol("") == ""


class TestFromFmpSymbol:
    @pytest.mark.parametrize(
        "fmp,internal",
        [
            ("BRK-B", "BRK.B"),
            ("BF-B", "BF.B"),
            ("AAPL", "AAPL"),   # passthrough (hyphen 없음)
        ],
    )
    def test_hyphen_to_dot(self, fmp, internal):
        assert from_fmp_symbol(fmp) == internal

    def test_none_and_empty_passthrough(self):
        assert from_fmp_symbol(None) is None
        assert from_fmp_symbol("") == ""


class TestRoundTrip:
    @pytest.mark.parametrize("internal", ["BRK.B", "BF.B", "AAPL", "MSFT"])
    def test_roundtrip_internal(self, internal):
        # 정본 → FMP → 정본 = 항등 (class-share·일반 심볼 모두)
        assert from_fmp_symbol(to_fmp_symbol(internal)) == internal


class TestSymbolsParam:
    def test_single(self):
        assert to_fmp_symbols_param("BRK.B") == "BRK-B"

    def test_comma_multi(self):
        assert to_fmp_symbols_param("AAPL,BRK.B,BF.B") == "AAPL,BRK-B,BF-B"

    def test_no_dot_passthrough(self):
        # 501 유니버스 동형 케이스 — 무변환
        assert to_fmp_symbols_param("AAPL,MSFT,GOOGL") == "AAPL,MSFT,GOOGL"

    def test_none_and_empty(self):
        assert to_fmp_symbols_param(None) is None
        assert to_fmp_symbols_param("") == ""


class TestRestoreSymbolsInResponse:
    """응답 경계 역변환 (Slice 1-3): FMP hyphen → 내부 정본 dot."""

    def test_list_of_dicts(self):
        data = [{"symbol": "BRK-B", "eps": 1}, {"symbol": "AAPL", "eps": 2}]
        out = restore_symbols_in_response(data)
        assert out[0]["symbol"] == "BRK.B"  # 복원
        assert out[1]["symbol"] == "AAPL"   # passthrough

    def test_single_dict(self):
        data = {"symbol": "BF-B", "price": 10}
        assert restore_symbols_in_response(data)["symbol"] == "BF.B"

    def test_no_symbol_field_untouched(self):
        data = {"price": 10, "date": "2026-07-31"}
        out = restore_symbols_in_response(data)
        assert out == {"price": 10, "date": "2026-07-31"}  # date 등 무접촉

    def test_empty_and_non_dict_items(self):
        assert restore_symbols_in_response([]) == []
        assert restore_symbols_in_response({}) == {}
        # 비-dict 항목 섞여도 안전
        assert restore_symbols_in_response([{"symbol": "BRK-B"}, "x"])[0]["symbol"] == "BRK.B"


class TestMakeRequestBoundaryIdentical:
    """
    IDENTICAL 게이트 (Slice 1-4): _make_request 요청 경계에서
    501 유니버스 심볼(dot 없음)의 요청 문자열이 변환 전후 동일함을 입증(행위보존).
    dot 심볼만 hyphen 변환.
    """

    def _client_capturing(self, monkeypatch):
        from packages.shared.api_request.providers.fmp import client as fmp_client

        captured = {}

        class _FakeResp:
            status_code = 200

            def json(self):
                return []

        def _fake_get(url, params=None, timeout=None):
            captured.clear()
            captured.update(params or {})
            return _FakeResp()

        monkeypatch.setattr(fmp_client.requests, "get", _fake_get)
        return fmp_client.FMPClient(api_key="test-key"), captured

    @pytest.mark.parametrize("sym", ["AAPL", "MSFT", "GOOGL", "JPM"])
    def test_non_dot_symbol_identical(self, monkeypatch, sym):
        client, captured = self._client_capturing(monkeypatch)
        client._make_request("/stable/quote", {"symbol": sym})
        assert captured["symbol"] == sym  # 변환 전후 동일 (행위보존)

    def test_dot_symbol_converted_to_hyphen(self, monkeypatch):
        client, captured = self._client_capturing(monkeypatch)
        client._make_request("/stable/quote", {"symbol": "BRK.B"})
        assert captured["symbol"] == "BRK-B"

    def test_symbols_key_also_converted(self, monkeypatch):
        client, captured = self._client_capturing(monkeypatch)
        client._make_request("/stable/news/stock", {"symbols": "BF.B"})
        assert captured["symbols"] == "BF-B"

    def test_no_symbol_param_untouched(self, monkeypatch):
        client, captured = self._client_capturing(monkeypatch)
        client._make_request("/stable/some-endpoint", {"period": "annual"})
        assert "symbol" not in captured and captured["period"] == "annual"
