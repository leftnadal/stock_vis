"""collect_av_broad_news 스펙 정렬(B) 회귀 — 전일 am/pm 2창 기본 + 명시 창 단발 보존.

핵심 계약:
- 무인자(beat) 호출 = 전일(UTC) am(00-12)/pm(12-24) 2창 EARLIEST 2호출 + 집계.
- 명시 time_from/time_to = 단발(백필 경로) — 기존 행위 보존.
- 배치1 러너와 동일 윈도우 정의(새 발명 없음).
"""
import datetime as dt
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from services.news.tasks import collect_av_broad_news


def _mocks(saved=5, updated=2, skipped=0, n_arts=3):
    prov = MagicMock()
    prov.fetch_broad_news.return_value = list(range(n_arts))  # len()만 사용
    agg = MagicMock()
    agg.deduplicator.deduplicate.side_effect = lambda arts: arts
    agg._save_articles.return_value = (saved, updated, skipped)
    return prov, agg


@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_no_args_fetches_yesterday_am_pm_two_windows():
    prov, agg = _mocks(saved=5)
    fixed_now = dt.datetime(2026, 7, 10, 1, 0, tzinfo=dt.timezone.utc)
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg), \
         patch("services.news.tasks.timezone") as mtz:
        mtz.now.return_value = fixed_now
        res = collect_av_broad_news.apply(kwargs={}).get()

    # 2창 = 2 호출
    assert prov.fetch_broad_news.call_count == 2
    calls = prov.fetch_broad_news.call_args_list
    # 전일 = 2026-07-09, am/pm UTC naive 윈도우 (배치1 정의)
    assert calls[0].kwargs["time_from"] == dt.datetime(2026, 7, 9, 0, 0)
    assert calls[0].kwargs["time_to"] == dt.datetime(2026, 7, 9, 12, 0)
    assert calls[1].kwargs["time_from"] == dt.datetime(2026, 7, 9, 12, 0)
    assert calls[1].kwargs["time_to"] == dt.datetime(2026, 7, 10, 0, 0)
    assert calls[0].kwargs["sort"] == "EARLIEST"
    # 집계 = 2창 합
    assert res["saved"] == 10
    assert res["fetched"] == 6
    assert "am+pm" in res["window"] and "2026-07-09" in res["window"]


@pytest.mark.django_db
@override_settings(ALPHA_VANTAGE_API_KEY="testkey")
def test_explicit_window_single_fetch_preserved():
    prov, agg = _mocks(saved=5)
    with patch("services.news.providers.alphavantage.AlphaVantageNewsProvider", return_value=prov), \
         patch("services.news.services.aggregator.NewsAggregatorService", return_value=agg):
        res = collect_av_broad_news.apply(kwargs={
            "time_from": "20260707T0000", "time_to": "20260707T1200", "sort": "EARLIEST",
        }).get()

    # 명시 창 = 단발
    assert prov.fetch_broad_news.call_count == 1
    call = prov.fetch_broad_news.call_args
    assert call.kwargs["time_from"] == dt.datetime(2026, 7, 7, 0, 0)
    assert call.kwargs["time_to"] == dt.datetime(2026, 7, 7, 12, 0)
    assert res["saved"] == 5
    assert res["window"] == "20260707T0000~20260707T1200"
