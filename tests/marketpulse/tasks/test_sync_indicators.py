"""Tests for marketpulse.tasks.sync_indicators."""
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from django.utils import timezone

from apps.market_pulse.tasks.sync_indicators import (
    FRED_RECURRING_SERIES,
    mp_sync_fred_indicators_daily,
    mp_sync_yahoo_indicators_daily,
)
from macro.models.indicators import EconomicIndicator, IndicatorValue


def _seed_indicators():
    for code in ('VIX3M', 'MOVE'):
        EconomicIndicator.objects.update_or_create(
            code=code,
            defaults={'name': code, 'data_source': 'fred'},
        )


def _df(rows):
    """rows = [(date, close)] → yfinance 형 DataFrame (multi-column 'Close')."""
    dates = pd.to_datetime([r[0] for r in rows])
    df = pd.DataFrame(
        {('Close',): [r[1] for r in rows]},
        index=pd.DatetimeIndex(dates, name='Date'),
    )
    df.columns = pd.MultiIndex.from_tuples([('Close',)])
    return df


@pytest.mark.django_db
class TestSyncYahooIndicators:
    def test_inserts_rows_for_both_series(self):
        _seed_indicators()
        fake_df = pd.DataFrame(
            {'Close': [21.0, 21.5, 20.7]},
            index=pd.to_datetime(['2026-04-25', '2026-04-26', '2026-04-27']),
        )
        with patch('yfinance.download', return_value=fake_df):
            result = mp_sync_yahoo_indicators_daily.apply().get()

        assert result['total_saved'] == 6  # 2 series × 3 rows
        assert IndicatorValue.objects.filter(
            indicator__code='VIX3M').count() == 3
        assert IndicatorValue.objects.filter(
            indicator__code='MOVE').count() == 3

    def test_idempotent(self):
        _seed_indicators()
        fake_df = pd.DataFrame(
            {'Close': [21.0]},
            index=pd.to_datetime(['2026-04-27']),
        )
        with patch('yfinance.download', return_value=fake_df):
            mp_sync_yahoo_indicators_daily.apply().get()
            second = mp_sync_yahoo_indicators_daily.apply().get()

        assert second['total_saved'] == 0  # update only
        assert IndicatorValue.objects.count() == 2

    def test_indicator_not_seeded_records_error(self):
        # 마이그레이션 시드된 VIX3M을 삭제, MOVE만 시드 보장
        EconomicIndicator.objects.filter(code='VIX3M').delete()
        EconomicIndicator.objects.update_or_create(
            code='MOVE', defaults={'name': 'MOVE', 'data_source': 'fred'},
        )
        fake_df = pd.DataFrame(
            {'Close': [21.0]}, index=pd.to_datetime(['2026-04-27']),
        )
        with patch('yfinance.download', return_value=fake_df):
            result = mp_sync_yahoo_indicators_daily.apply().get()

        assert result['series']['VIX3M']['error'] == 'indicator_not_seeded'
        assert 'fetched' in result['series']['MOVE']

    def test_empty_df_marks_error(self):
        _seed_indicators()
        empty = pd.DataFrame()
        with patch('yfinance.download', return_value=empty):
            result = mp_sync_yahoo_indicators_daily.apply().get()

        for code in ('VIX3M', 'MOVE'):
            assert result['series'][code]['error'] == 'empty'
        assert result['total_saved'] == 0


# ── MP-DATA-MACRO-COVERAGE: FRED 7종 재귀 동기화 (M-1) ──────────────────────

def _seed_fred():
    for code in FRED_RECURRING_SERIES:
        EconomicIndicator.objects.update_or_create(
            code=code, defaults={'name': code, 'data_source': 'fred'},
        )


FAKE_OBS = [
    {'date': '2026-06-16', 'value': '1.5'},
    {'date': '2026-06-17', 'value': '1.6'},
]


@pytest.mark.django_db
class TestSyncFredIndicators:
    def test_syncs_7_scoped_series(self):
        _seed_fred()
        with patch('packages.shared.api_request.fred_client.FREDClient') as MockClient:
            MockClient.return_value.get_series_observations.return_value = FAKE_OBS
            result = mp_sync_fred_indicators_daily.apply().get()

        assert set(result['series']) == set(FRED_RECURRING_SERIES)
        assert len(result['series']) == 7  # NFCI×4 + HY pair + T10Y3M
        for code in FRED_RECURRING_SERIES:
            assert IndicatorValue.objects.filter(indicator__code=code).count() == 2

    def test_scope_excludes_yahoo_series(self):
        # VIX3M·MOVE는 mp_sync_yahoo_indicators_daily 담당 → FRED 재귀서 제외(미지원/중복 회피)
        assert 'VIX3M' not in FRED_RECURRING_SERIES
        assert 'MOVE' not in FRED_RECURRING_SERIES

    def test_idempotent(self):
        _seed_fred()
        with patch('packages.shared.api_request.fred_client.FREDClient') as MockClient:
            MockClient.return_value.get_series_observations.return_value = FAKE_OBS
            mp_sync_fred_indicators_daily.apply().get()
            mp_sync_fred_indicators_daily.apply().get()  # 2회

        # update_or_create → 2회 실행해도 행 수 불변 (7 series × 2 obs)
        assert IndicatorValue.objects.count() == 14


@pytest.mark.django_db
def test_fred_task_registered_in_beat():
    """setup_marketpulse_beat가 신규 FRED task를 PeriodicTask로 등록(Bug #28: DB 직접)."""
    from django.core.management import call_command
    from django_celery_beat.models import PeriodicTask

    call_command('setup_marketpulse_beat')
    t = PeriodicTask.objects.filter(name='mp_sync_fred_indicators_daily').first()
    assert t is not None
    assert t.task == 'apps.market_pulse.tasks.sync_indicators.mp_sync_fred_indicators_daily'
    assert t.enabled is True
