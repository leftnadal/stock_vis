"""SFI-I1 Part 3 — nightly ingest 태스크 + 카운터 소진 중단 방어.

태스크는 유니버스(보유∪관심)를 capture_symbols에 배선(수집 mock). 카운터 소진
(FMPRateLimitError)은 터미널 → 남은 심볼 미시도(중단).
"""
from unittest.mock import Mock

import pytest

from apps.portfolio import tasks as portfolio_tasks
from packages.shared.api_request.providers.fmp.client import FMPRateLimitError
from packages.shared.stocks.models import AnalystSignalSnapshot
from packages.shared.stocks.services.analyst_signal_writer import capture_symbols


def test_task_wires_universe_into_capture(monkeypatch):
    captured_args = {}

    def fake_capture(client, symbols):
        captured_args["symbols"] = list(symbols)
        return {"captured": 2, "failed": 0, "skipped": 0,
                "halted_rate_limit": False, "errors": {}}

    monkeypatch.setattr(portfolio_tasks, "_coach_universe", lambda: ["AAPL", "TLN"])
    monkeypatch.setattr(portfolio_tasks, "capture_symbols", fake_capture)
    monkeypatch.setattr(portfolio_tasks, "FMPClient", lambda api_key=None: Mock())

    result = portfolio_tasks.ingest_analyst_signals.apply().get()

    assert captured_args["symbols"] == ["AAPL", "TLN"]
    assert result["universe"] == 2
    assert result["captured"] == 2


def test_task_empty_universe_skips(monkeypatch):
    monkeypatch.setattr(portfolio_tasks, "_coach_universe", lambda: [])
    called = {"n": 0}
    monkeypatch.setattr(
        portfolio_tasks, "capture_symbols",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1),
    )
    result = portfolio_tasks.ingest_analyst_signals.apply().get()
    assert result["universe"] == 0
    assert called["n"] == 0  # 유니버스 비면 client·capture 미호출


class RateLimitedClient:
    """N번째 심볼에서 카운터 소진 → FMPRateLimitError."""

    def __init__(self, limit_on):
        self.limit_on = limit_on.upper()

    def _g(self, s):
        if s.upper() == self.limit_on:
            raise FMPRateLimitError("Daily API limit exceeded")

    def get_ratings_snapshot(self, s):
        self._g(s)
        return {"rating": "B", "overallScore": 3}

    def get_price_target_consensus(self, s):
        self._g(s)
        return {"targetConsensus": 340.53, "targetHigh": 400, "targetLow": 245,
                "targetMedian": 350}

    def get_grades_consensus(self, s):
        self._g(s)
        return {"strongBuy": 1, "buy": 70, "hold": 32, "sell": 8, "strongSell": 0,
                "consensus": "Buy"}

    def get_grades_historical(self, s, limit=12):
        self._g(s)
        return [{"date": "2025-07-01", "analystRatingsBuy": 70}]


@pytest.mark.django_db
def test_capture_symbols_halts_on_rate_limit():
    client = RateLimitedClient(limit_on="GEV")
    summary = capture_symbols(client, ["AAPL", "GEV", "TLN"])

    assert summary["captured"] == 1                 # AAPL만
    assert summary["halted_rate_limit"] is True
    assert "GEV" in summary["errors"]
    # 중단 이후 TLN은 시도조차 안 함 → DB 무행
    assert AnalystSignalSnapshot.objects.filter(symbol="AAPL").count() == 1
    assert AnalystSignalSnapshot.objects.filter(symbol="TLN").count() == 0
