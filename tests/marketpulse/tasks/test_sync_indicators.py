"""Tests for marketpulse.tasks.sync_indicators."""
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from django.utils import timezone

from macro.models.indicators import EconomicIndicator, IndicatorValue
from marketpulse.tasks.sync_indicators import mp_sync_yahoo_indicators_daily


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
