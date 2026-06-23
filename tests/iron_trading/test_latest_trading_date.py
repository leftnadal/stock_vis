"""iron-trading /api/v1/iron-trading/latest-trading-date 계약 테스트 (방안 B).

read-only. daily-context 200을 보장하는 최신 거래일을 산출한다.
방안 B 핵심: 단순 최댓값이 아니라 dry-check로 라운드트립 200을 구조로 보장.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

ENDPOINT = "/api/v1/iron-trading/latest-trading-date"
DAILY_CONTEXT = "/api/v1/iron-trading/daily-context"


# ---------------------------------------------------------------------------
# Helpers (daily-context 테스트와 동일한 시드 패턴)
# ---------------------------------------------------------------------------


def _seed_us_stock(symbol: str, sector: str = "Technology", price: str = "100.00"):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(
        symbol=symbol,
        stock_name=f"{symbol} Inc.",
        exchange="NASDAQ",
        currency="USD",
        sector=sector,
        industry=f"{sector} sub",
        real_time_price=Decimal(price),
    )


def _seed_prices(stock, end_date: date, days: int = 30, base: float = 100.0):
    from packages.shared.stocks.models import DailyPrice

    rows = []
    d = end_date - timedelta(days=days - 1)
    for i in range(days):
        price = Decimal(str(base + i * 0.5))
        rows.append(
            DailyPrice(
                stock=stock,
                date=d + timedelta(days=i),
                open_price=price - Decimal("0.5"),
                high_price=price + Decimal("0.5"),
                low_price=price - Decimal("1.0"),
                close_price=price,
                volume=1_000_000 + i * 10_000,
            )
        )
    DailyPrice.objects.bulk_create(rows)
    return rows


def _seed_eod_signal(stock, signal_date: date, composite: float, count: int = 3):
    from packages.shared.stocks.models import EODSignal

    return EODSignal.objects.create(
        stock=stock,
        date=signal_date,
        signals=[{"id": "V1", "category": "volume"}] * count,
        tag_details={"primary": "V1"},
        signal_count=count,
        bullish_count=count,
        bearish_count=0,
        composite_score=composite,
        close_price=Decimal("130.00"),
        change_percent=1.5,
        volume=2_000_000,
        dollar_volume=Decimal("260000000.00"),
        sector=stock.sector or "",
        industry=stock.industry or "",
    )


def _seed_running_pipeline(d: date):
    from packages.shared.stocks.models import PipelineLog

    return PipelineLog.objects.create(
        date=d,
        status="running",
        started_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def api_client():
    return APIClient()


# ---------------------------------------------------------------------------
# 1. 200 성공 — 최신 daily-context 가능 날짜 반환
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLatestTradingDate:
    def test_returns_latest_available_date(self, api_client):
        latest = date(2026, 5, 22)
        older = date(2026, 5, 20)
        nvda = _seed_us_stock("NVDA")
        _seed_prices(nvda, latest, days=40, base=900.0)
        _seed_eod_signal(nvda, older, composite=0.5)
        _seed_eod_signal(nvda, latest, composite=0.72)

        resp = api_client.get(ENDPOINT)
        assert resp.status_code == 200
        body = resp.json()
        assert body["schema_version"] == "1.0"
        assert body["provider"] == "stock_vis"
        assert body["universe"] == "us_core"
        assert body["market_timezone"] == "America/New_York"
        assert body["latest_trading_date"] == "2026-05-22"
        assert body["selection_policy"] == "latest_daily_context_available"
        dc = body["daily_context"]
        assert dc["available"] is True
        assert dc["freshness_status"] == "unknown"
        assert dc["snapshot_id"] == ""
        assert dc["warnings"] == []
        assert "date=2026-05-22" in dc["url"]

    # -------------------------------------------------------------------
    # 2. round-trip — 반환 날짜로 daily-context 호출 시 200
    # -------------------------------------------------------------------
    def test_round_trip_daily_context_200(self, api_client):
        latest = date(2026, 5, 22)
        nvda = _seed_us_stock("NVDA")
        _seed_prices(nvda, latest, days=40, base=900.0)
        _seed_eod_signal(nvda, latest, composite=0.6)

        resp = api_client.get(ENDPOINT)
        assert resp.status_code == 200
        resolved = resp.json()["latest_trading_date"]

        dc = api_client.get(DAILY_CONTEXT, {"date": resolved})
        assert dc.status_code == 200
        assert dc.json()["trading_date"] == resolved
        assert len(dc.json()["candidates"]) >= 1

    # -------------------------------------------------------------------
    # 3. 400 — unsupported universe
    # -------------------------------------------------------------------
    def test_unsupported_universe_returns_400(self, api_client):
        resp = api_client.get(ENDPOINT, {"universe": "kr_core"})
        assert resp.status_code == 400
        body = resp.json()
        assert body["provider"] == "stock_vis"
        assert body["error"]["code"] == "unsupported_universe"

    # -------------------------------------------------------------------
    # 4. 404 — 사용 가능한 날짜가 전혀 없음
    # -------------------------------------------------------------------
    def test_no_dates_returns_404(self, api_client):
        resp = api_client.get(ENDPOINT)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "latest_trading_date_not_found"

    # -------------------------------------------------------------------
    # 5. fallback 200 — 최신일 running + 직전 완료일 존재 → 직전 완료일 반환
    # -------------------------------------------------------------------
    def test_fallback_when_latest_building(self, api_client):
        latest = date(2026, 5, 22)
        prev = date(2026, 5, 20)
        nvda = _seed_us_stock("NVDA")
        # 두 날짜 모두 후보+OHLCV 성립
        _seed_prices(nvda, latest, days=40, base=900.0)
        _seed_eod_signal(nvda, prev, composite=0.5)
        _seed_eod_signal(nvda, latest, composite=0.7)
        # 최신일은 pipeline building
        _seed_running_pipeline(latest)

        resp = api_client.get(ENDPOINT)
        assert resp.status_code == 200
        assert resp.json()["latest_trading_date"] == "2026-05-20"

    # -------------------------------------------------------------------
    # 6. ★ 비정렬 200 (방안 B 핵심) — 최신일에 EODSignal은 있으나 후보·OHLCV가
    #    없어 dry-check 실패 → skip 하고 직전 유효일을 200으로 반환.
    #    (방안 A였다면 깨졌을 케이스를 명시적으로 고정.)
    # -------------------------------------------------------------------
    def test_misaligned_latest_skipped_via_dry_check(self, api_client):
        latest = date(2026, 5, 22)
        valid = date(2026, 5, 20)
        nvda = _seed_us_stock("NVDA")

        # 직전 유효일: 후보 + OHLCV 모두 존재
        _seed_prices(nvda, valid, days=40, base=900.0)
        _seed_eod_signal(nvda, valid, composite=0.6)

        # 최신일: EODSignal은 있으나 그 날 OHLCV(DailyPrice)가 전혀 없는 KRW-only 등
        # 으로 후보+OHLCV 미성립. 여기선 OHLCV 없는 EODSignal만 둔다.
        ghost = _seed_us_stock("GHOST")
        _seed_eod_signal(ghost, latest, composite=0.9)
        # GHOST는 latest 날짜 lookback 범위 내 DailyPrice가 하나도 없음 → dry-check 실패

        resp = api_client.get(ENDPOINT)
        assert resp.status_code == 200
        # 방안 A(단순 최댓값)였다면 2026-05-22를 반환해 round-trip이 503으로 깨짐.
        assert resp.json()["latest_trading_date"] == "2026-05-20"

        # round-trip도 200이어야 함 (구조 보장 입증)
        dc = api_client.get(DAILY_CONTEXT, {"date": resp.json()["latest_trading_date"]})
        assert dc.status_code == 200
