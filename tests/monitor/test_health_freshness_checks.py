"""PRICE-FRESH-1-B §B — health_check 신규 2항목의 임계 판정.

B-1(수집 층)과 B-2(이식 층)는 실패 지점이 다르다 — 가격이 도착해도 ingest가 밀리면
판독값만 묵는다. 두 항목을 한 항목으로 묶으면 GEV처럼 MonitorSnapshot.asof가 최신인데
구성 지표가 4거래일 묵은 상태를 놓친다(2026-09-22 실측).
"""
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from health_check import (  # noqa: E402
    OK,
    PRICE_INPUT_STALE_DAYS,
    WARN,
    check_indicator_reading_freshness,
    check_price_input_freshness,
)

User = get_user_model()
BASE = date(2026, 9, 21)


@pytest.fixture
def stock(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="ZZTEST", stock_name="ZZ Test")


@pytest.fixture
def monitor(db, stock):
    from apps.monitor.models import Monitor

    u = User.objects.create_user(username="hc_user", password="pw12345")
    return Monitor.objects.create(
        user=u, scope="stock", target_ref="ZZTEST", name="테스트", current_state="active"
    )


@pytest.fixture
def mk_daily(stock):
    from packages.shared.stocks.models import DailyPrice

    def _mk(d, close=100.0):
        DailyPrice.objects.create(
            stock=stock, date=d,
            open_price=Decimal(str(close)), high_price=Decimal(str(close)),
            low_price=Decimal(str(close)), close_price=Decimal(str(close)),
            volume=1_000_000,
        )
    return _mk


@pytest.fixture
def mk_eod(stock):
    from packages.shared.stocks.models import EODSignal

    def _mk(d, close=100.0):
        EODSignal.objects.create(stock=stock, date=d, close_price=Decimal(str(close)))
    return _mk


# ── B-1: 가격 입력 신선도 — 갭 0·1·2·4일 경계 ────────────────────────────────

@pytest.mark.django_db
class TestPriceInputFreshness:
    def test_threshold_is_three_days(self):
        assert PRICE_INPUT_STALE_DAYS == 3

    def test_gap_zero_is_ok(self, monitor, mk_eod, mk_daily):
        mk_eod(BASE); mk_daily(BASE)
        assert check_price_input_freshness().status == OK

    def test_gap_one_is_ok(self, monitor, mk_eod, mk_daily):
        mk_eod(BASE - timedelta(days=1)); mk_daily(BASE)
        assert check_price_input_freshness().status == OK

    def test_gap_at_threshold_is_ok(self, monitor, mk_eod, mk_daily):
        """경계: 갭 == 임계는 통과(주말 흡수 — 금요일 판독 → 월요일 점검)."""
        mk_eod(BASE - timedelta(days=PRICE_INPUT_STALE_DAYS)); mk_daily(BASE)
        assert check_price_input_freshness().status == OK

    def test_gap_over_threshold_warns(self, monitor, mk_eod, mk_daily):
        """★ GEV 재현: EODSignal 4일 뒤처짐 → WARN + 종목명·일수 나열."""
        mk_eod(BASE - timedelta(days=4)); mk_daily(BASE)
        r = check_price_input_freshness()
        assert r.status == WARN
        assert any("ZZTEST" in e and "4일" in e for e in r.evidence)

    def test_missing_one_source_warns(self, monitor, mk_daily):
        mk_daily(BASE)
        r = check_price_input_freshness()
        assert r.status == WARN
        assert any("한쪽 부재" in e for e in r.evidence)

    def test_no_active_monitor_is_ok_skip(self, db):
        r = check_price_input_freshness()
        assert r.status == OK
        assert "검사 생략" in r.detail


# ── B-2: 지표 판독 신선도 ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestIndicatorReadingFreshness:
    @pytest.fixture
    def indicator(self, monitor):
        from apps.monitor.models import MonitorIndicator

        return MonitorIndicator.objects.create(
            monitor=monitor, name="지표", source_key="eod_composite",
            indicator_type=MonitorIndicator.IndicatorType.MARKET_DATA,
            support_direction=MonitorIndicator.SupportDirection.POSITIVE, weight=1.0,
        )

    def _reading(self, indicator, d, value=1.0):
        from apps.monitor.models import IndicatorReading

        IndicatorReading.objects.create(
            indicator=indicator, value=value,
            asof=timezone.make_aware(timezone.datetime(d.year, d.month, d.day, 0, 0)),
            validation_status="ok",
        )

    def test_fresh_reading_is_ok(self, indicator, mk_daily):
        mk_daily(BASE)
        self._reading(indicator, BASE)
        assert check_indicator_reading_freshness().status == OK

    def test_at_threshold_is_ok(self, indicator, mk_daily):
        mk_daily(BASE)
        self._reading(indicator, BASE - timedelta(days=PRICE_INPUT_STALE_DAYS))
        assert check_indicator_reading_freshness().status == OK

    def test_over_threshold_warns_with_symbol_and_key(self, indicator, mk_daily):
        """★ GEV 재현: 판독값 4일 뒤처짐 → 종목명/지표명/일수 나열."""
        mk_daily(BASE)
        self._reading(indicator, BASE - timedelta(days=4))
        r = check_indicator_reading_freshness()
        assert r.status == WARN
        assert any("ZZTEST" in e and "eod_composite" in e and "4일" in e for e in r.evidence)

    def test_zero_readings_warns(self, indicator, mk_daily):
        mk_daily(BASE)
        r = check_indicator_reading_freshness()
        assert r.status == WARN
        assert any("판독값 0건" in e for e in r.evidence)

    def test_independent_from_price_layer(self, indicator, mk_eod, mk_daily):
        """★ 두 항목을 묶으면 안 되는 이유 — 가격은 정상인데 판독값만 묵는다."""
        mk_eod(BASE); mk_daily(BASE)                       # 수집 층 정상
        self._reading(indicator, BASE - timedelta(days=4))  # 이식 층만 지연
        assert check_price_input_freshness().status == OK
        assert check_indicator_reading_freshness().status == WARN

    def test_no_active_monitor_is_ok_skip(self, db):
        r = check_indicator_reading_freshness()
        assert r.status == OK
        assert "검사 생략" in r.detail
