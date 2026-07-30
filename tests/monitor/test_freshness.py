"""신선도 게이트 검증 (D-EOD-FRESH, B안 — beat 자가 신선도 보장).

비편입 보유 종목의 DailyPrice가 stale이면 refresh_monitors 서두에서 온디맨드 보충.
외부 FMP 호출은 mock — sync_prices 호출/격리 동작만 검증(as_of 시그니처 버그 교훈:
통합 경로를 실 시그니처로 검증).
"""
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.monitor.models import Monitor
from apps.monitor.services.pipeline import (
    _expected_last_trading_day,
    ensure_price_freshness,
    refresh_monitors,
)


def _make_daily(stock, d, close="100"):
    from packages.shared.stocks.models import DailyPrice

    return DailyPrice.objects.create(
        stock=stock,
        date=d,
        open_price=Decimal(close),
        high_price=Decimal(close),
        low_price=Decimal(close),
        close_price=Decimal(close),
        volume=1000,
    )


def _make_stock(symbol):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol=symbol, stock_name=symbol)


# ── P1-5 유닛: 거래일 경계 ────────────────────────────────────────────────
class TestExpectedLastTradingDay:
    def test_weekday_prev_day(self):
        # 화요일 2026-07-28 → 직전 거래일 월요일 07-27
        assert _expected_last_trading_day(datetime.date(2026, 7, 28)) == datetime.date(2026, 7, 27)

    def test_monday_skips_weekend(self):
        # 월요일 2026-07-27 → 일·토 건너뛰고 금요일 07-24
        assert _expected_last_trading_day(datetime.date(2026, 7, 27)) == datetime.date(2026, 7, 24)

    def test_sunday_to_friday(self):
        # 일요일 2026-07-26 → 금요일 07-24
        assert _expected_last_trading_day(datetime.date(2026, 7, 26)) == datetime.date(2026, 7, 24)

    def test_saturday_to_friday(self):
        assert _expected_last_trading_day(datetime.date(2026, 7, 25)) == datetime.date(2026, 7, 24)


# ── P1-5 유닛: 신선도 판정 + 실패 격리 ────────────────────────────────────
@pytest.mark.django_db
class TestEnsurePriceFreshness:
    def test_stale_symbol_synced(self):
        stock = _make_stock("STALE")
        _make_daily(stock, datetime.date(2026, 6, 1))  # 45일 stale
        with patch("packages.shared.stocks.services.stock_sync_service.StockSyncService") as MockSvc:
            MockSvc.return_value.sync_prices.return_value = MagicMock(success=True)
            summary = ensure_price_freshness(["STALE"], as_of_date=datetime.date(2026, 7, 28))
            MockSvc.return_value.sync_prices.assert_called_once_with("STALE", days=90, force=True)
        assert summary["synced"] == ["STALE"]
        assert summary["skipped_fresh"] == []

    def test_fresh_symbol_skipped(self):
        stock = _make_stock("FRESH")
        _make_daily(stock, datetime.date(2026, 7, 27))  # 월요일(직전 거래일) = fresh vs 화 07-28
        with patch("packages.shared.stocks.services.stock_sync_service.StockSyncService") as MockSvc:
            summary = ensure_price_freshness(["FRESH"], as_of_date=datetime.date(2026, 7, 28))
            MockSvc.return_value.sync_prices.assert_not_called()  # no-op
        assert summary["skipped_fresh"] == ["FRESH"]
        assert summary["synced"] == []

    def test_no_daily_row_treated_stale(self):
        _make_stock("NEW")  # DailyPrice 0행 → stale로 sync 시도
        with patch("packages.shared.stocks.services.stock_sync_service.StockSyncService") as MockSvc:
            MockSvc.return_value.sync_prices.return_value = MagicMock(success=True)
            summary = ensure_price_freshness(["NEW"], as_of_date=datetime.date(2026, 7, 28))
        assert summary["synced"] == ["NEW"]

    def test_failure_isolated_others_continue(self):
        s1 = _make_stock("BAD")
        s2 = _make_stock("GOOD")
        _make_daily(s1, datetime.date(2026, 6, 1))
        _make_daily(s2, datetime.date(2026, 6, 1))

        def _side_effect(symbol, **kwargs):
            if symbol == "BAD":
                raise RuntimeError("FMP 폭발")
            return MagicMock(success=True)

        with patch("packages.shared.stocks.services.stock_sync_service.StockSyncService") as MockSvc:
            MockSvc.return_value.sync_prices.side_effect = _side_effect
            # 예외가 전파되지 않아야 한다 (beat 본체 보호 #65)
            summary = ensure_price_freshness(["BAD", "GOOD"], as_of_date=datetime.date(2026, 7, 28))
        assert summary["failed"] == ["BAD"]
        assert summary["synced"] == ["GOOD"]
        assert summary["checked"] == 2

    def test_sync_returns_failure_recorded_not_raised(self):
        stock = _make_stock("SOFTFAIL")
        _make_daily(stock, datetime.date(2026, 6, 1))
        with patch("packages.shared.stocks.services.stock_sync_service.StockSyncService") as MockSvc:
            MockSvc.return_value.sync_prices.return_value = MagicMock(success=False, error="쿼터")
            summary = ensure_price_freshness(["SOFTFAIL"], as_of_date=datetime.date(2026, 7, 28))
        assert summary["failed"] == ["SOFTFAIL"]


# ── P1-6 통합 + P1-7 행위보존 ─────────────────────────────────────────────
@pytest.mark.django_db
class TestRefreshMonitorsGate:
    def test_refresh_monitors_invokes_gate_stale_symbol(self, user=None):
        # 비편입 stale 종목 모니터 포함 → refresh_monitors 실 시그니처 1회, 게이트가 sync 호출
        from django.contrib.auth import get_user_model

        u = get_user_model().objects.create_user(username="fresh_u", password="pw12345")
        stock = _make_stock("OFFIDX")
        _make_daily(stock, datetime.date(2026, 6, 1))
        Monitor.objects.create(
            user=u, scope=Monitor.Scope.STOCK, target_ref="OFFIDX", name="비편입"
        )
        with patch("packages.shared.stocks.services.stock_sync_service.StockSyncService") as MockSvc:
            MockSvc.return_value.sync_prices.return_value = MagicMock(success=True)
            # 실 시그니처 그대로 호출 — 예외 없이 완주해야 한다
            results = refresh_monitors(as_of_date=datetime.date(2026, 7, 28))
            MockSvc.return_value.sync_prices.assert_called_once_with("OFFIDX", days=90, force=True)
        assert isinstance(results, list)

    def test_gate_noop_when_all_fresh(self):
        from django.contrib.auth import get_user_model

        u = get_user_model().objects.create_user(username="fresh_u2", password="pw12345")
        stock = _make_stock("FRESHIDX")
        _make_daily(stock, datetime.date(2026, 7, 27))  # fresh
        Monitor.objects.create(
            user=u, scope=Monitor.Scope.STOCK, target_ref="FRESHIDX", name="최신"
        )
        with patch("packages.shared.stocks.services.stock_sync_service.StockSyncService") as MockSvc:
            refresh_monitors(as_of_date=datetime.date(2026, 7, 28))
            MockSvc.return_value.sync_prices.assert_not_called()  # 전 심볼 최신 → 게이트 no-op
