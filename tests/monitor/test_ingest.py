"""EODSignal → IndicatorReading 이식 검증 (MON-P2-INGEST)."""
from datetime import date, timedelta

import pytest
from django.core.management import call_command

from apps.monitor.models import IndicatorReading, Monitor
from apps.monitor.services.ingest import (
    ingest_readings_for_indicator,
    ingest_readings_for_monitor,
)


@pytest.fixture
def stock_aapl(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="AAPL", stock_name="Apple Inc.")


@pytest.fixture
def eod_series(stock_aapl):
    """AAPL EODSignal 시계열 (오늘 기준 역순 n일)."""
    from packages.shared.stocks.models import EODSignal

    def _make(n=10, with_null_at=None):
        rows = []
        for i in range(n):
            d = date.today() - timedelta(days=(n - 1 - i))
            comp = None if with_null_at == i else round(-1 + 2 * i / max(n - 1, 1), 4)
            rows.append(
                EODSignal.objects.create(
                    stock=stock_aapl,
                    date=d,
                    close_price=100 + i,
                    composite_score=comp if comp is not None else 0.0,
                    change_percent=float(i),
                    dollar_volume=1000 * (i + 1),
                )
            )
            if with_null_at == i:
                # composite_score는 non-null 필드라 null 케이스는 change_percent로 검증 불가 —
                # 대신 별도 테스트에서 getattr None 경로를 직접 확인.
                pass
        return rows

    return _make


@pytest.fixture
def aapl_monitor(stock_aapl):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(username="ing", password="pw12345")
    m = Monitor.objects.create(
        user=user, scope="stock", target_ref="AAPL", name="애플", current_state="active"
    )
    ind = m.indicators.create(
        name="EOD 종합 신호",
        indicator_type="market_data",
        source_key="eod_composite",
    )
    return m, ind


@pytest.mark.django_db
class TestIngest:
    def test_backfill_creates_readings(self, aapl_monitor, eod_series):
        eod_series(n=10)
        _, ind = aapl_monitor
        res = ingest_readings_for_indicator(ind)
        assert res["status"] == "ok"
        assert res["ingested"] == 10
        assert IndicatorReading.objects.filter(indicator=ind).count() == 10

    def test_idempotent_rerun(self, aapl_monitor, eod_series):
        eod_series(n=8)
        _, ind = aapl_monitor
        ingest_readings_for_indicator(ind)
        ingest_readings_for_indicator(ind)  # 재실행 → upsert, dup 없음
        assert IndicatorReading.objects.filter(indicator=ind).count() == 8

    def test_incremental_after_new_day(self, aapl_monitor, eod_series, stock_aapl):
        from packages.shared.stocks.models import EODSignal

        eod_series(n=5)
        _, ind = aapl_monitor
        ingest_readings_for_indicator(ind)
        assert IndicatorReading.objects.filter(indicator=ind).count() == 5
        # 새 거래일 추가 → 재실행 시 증분 1 (upsert)
        EODSignal.objects.create(
            stock=stock_aapl,
            date=date.today() + timedelta(days=1),
            close_price=200,
            composite_score=0.5,
        )
        ingest_readings_for_indicator(ind, as_of_date=date.today() + timedelta(days=1))
        assert IndicatorReading.objects.filter(indicator=ind).count() == 6

    def test_skip_non_stock_scope(self, aapl_monitor):
        m, ind = aapl_monitor
        m.scope = "fund"
        m.save()
        res = ingest_readings_for_indicator(ind)
        assert res["status"] == "skip_non_stock"

    def test_skip_no_source_key(self, aapl_monitor, eod_series):
        eod_series(n=5)
        m, _ = aapl_monitor
        custom = m.indicators.create(
            name="사용자", indicator_type="custom", source_key=""
        )
        res = ingest_readings_for_indicator(custom)
        assert res["status"] == "skip_no_source"

    def test_unknown_symbol(self, db):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username="u2", password="pw12345")
        m = Monitor.objects.create(
            user=user, scope="stock", target_ref="NOPE", name="x", current_state="active"
        )
        ind = m.indicators.create(
            name="i", indicator_type="market_data", source_key="eod_composite"
        )
        res = ingest_readings_for_indicator(ind)
        assert res["status"] == "skip_unknown_symbol"

    def test_no_data_in_range(self, aapl_monitor):
        # 종목은 있으나 EODSignal 없음
        _, ind = aapl_monitor
        res = ingest_readings_for_indicator(ind)
        assert res["status"] == "no_data_in_range"


@pytest.mark.django_db
class TestRefreshChaining:
    def test_ingest_then_evaluate_produces_score(self, aapl_monitor, eod_series):
        from apps.monitor.models import MonitorSnapshot
        from apps.monitor.services.pipeline import evaluate_monitor

        eod_series(n=12)
        m, ind = aapl_monitor
        ingest_readings_for_monitor(m)
        res = evaluate_monitor(m)
        # 판독 12개(상승 시계열) → 충분·비영 점수 + 스냅샷 생성
        snap = MonitorSnapshot.objects.get(monitor=m)
        assert snap.overall_score == res["overall_score"]
        assert res["data_coverage"] == 1.0

    def test_refresh_command_runs(self, aapl_monitor, eod_series):
        eod_series(n=10)
        m, _ = aapl_monitor
        call_command("refresh_monitors", "--monitor", str(m.id))
        from apps.monitor.models import MonitorSnapshot

        assert MonitorSnapshot.objects.filter(monitor=m).exists()
