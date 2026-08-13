"""I3-SPLIT-GUARD (D-SPLIT-1) — FMP 래퍼 + ingest 태스크 테스트.

래퍼(get_stock_splits) 파싱은 _make_request mock으로, ingest 멱등·skip은 DB로 검증.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from apps.portfolio import tasks as portfolio_tasks
from packages.shared.api_request.providers.fmp.client import FMPClient


# ── FMP 래퍼 파싱 ──
def test_get_stock_splits_parses_list(monkeypatch):
    client = FMPClient(api_key="test")
    payload = [
        {"symbol": "NVDA", "date": "2024-06-10", "numerator": 10, "denominator": 1,
         "splitType": "stock-split"},
    ]
    monkeypatch.setattr(client, "_make_request", lambda ep, params=None: payload)
    assert client.get_stock_splits("nvda") == payload


def test_get_stock_splits_non_list_returns_empty(monkeypatch):
    client = FMPClient(api_key="test")
    monkeypatch.setattr(client, "_make_request", lambda ep, params=None: {})
    assert client.get_stock_splits("GEV") == []


# ── ingest 태스크 (멱등·append/skip) ──
def _fake_client_with(rows):
    c = Mock()
    c.get_stock_splits.return_value = rows
    return c


@pytest.mark.django_db
def test_ingest_creates_and_is_idempotent(monkeypatch):
    from django.db import connections

    from packages.shared.stocks.models import Stock, StockSplit

    # close_all()(fork 안전, 버그 #25)은 test 트랜잭션 연결을 끊으므로 테스트에선 no-op
    monkeypatch.setattr(connections, "close_all", lambda: None)
    Stock.objects.create(symbol="NVDA", currency="USD")
    rows = [
        {"symbol": "NVDA", "date": "2024-06-10", "numerator": 10, "denominator": 1,
         "splitType": "stock-split"},
        {"symbol": "NVDA", "date": "2021-07-20", "numerator": 4, "denominator": 1,
         "splitType": "stock-split"},
    ]
    monkeypatch.setattr(portfolio_tasks, "_coach_universe", lambda: ["NVDA"])
    monkeypatch.setattr(portfolio_tasks, "FMPClient", lambda api_key=None: _fake_client_with(rows))

    r1 = portfolio_tasks.ingest_stock_splits.apply().get()
    assert r1["created"] == 2 and r1["fetched"] == 2 and r1["skipped"] == 0
    assert StockSplit.objects.filter(stock__symbol="NVDA").count() == 2

    # 재실행 = append-only → 신규 0, 전부 skip, 행수 불변
    r2 = portfolio_tasks.ingest_stock_splits.apply().get()
    assert r2["created"] == 0 and r2["skipped"] == 2
    assert StockSplit.objects.filter(stock__symbol="NVDA").count() == 2


@pytest.mark.django_db
def test_ingest_skips_when_stock_absent(monkeypatch):
    from django.db import connections

    from packages.shared.stocks.models import StockSplit

    monkeypatch.setattr(connections, "close_all", lambda: None)
    rows = [{"symbol": "ZZZ", "date": "2024-01-01", "numerator": 2, "denominator": 1,
             "splitType": "stock-split"}]
    monkeypatch.setattr(portfolio_tasks, "_coach_universe", lambda: ["ZZZ"])
    monkeypatch.setattr(portfolio_tasks, "FMPClient", lambda api_key=None: _fake_client_with(rows))

    r = portfolio_tasks.ingest_stock_splits.apply().get()
    assert r["created"] == 0 and r["skipped"] == 1
    assert StockSplit.objects.count() == 0


def test_ingest_empty_universe_skips(monkeypatch):
    monkeypatch.setattr(portfolio_tasks, "_coach_universe", lambda: [])
    r = portfolio_tasks.ingest_stock_splits.apply().get()
    assert r == {"symbols": 0, "fetched": 0, "created": 0, "skipped": 0, "errors": {}}
