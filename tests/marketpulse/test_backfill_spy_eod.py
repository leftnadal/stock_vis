"""A-PREP — backfill_spy_eod 커맨드 회귀 (FMP mock).

계약: dry-run 무쓰기·멱등(재실행 삽입 0)·창 필터·기존 skip·shared 래퍼 경유.
"""

from __future__ import annotations

from datetime import date
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

pytestmark = [pytest.mark.django_db]


@pytest.fixture(autouse=True)
def _clean():
    from macro.models.indicators import MarketIndexPrice

    MarketIndexPrice.objects.all().delete()
    yield


@pytest.fixture
def spy_index():
    from macro.models.indicators import MarketIndex

    idx, _ = MarketIndex.objects.get_or_create(symbol="SPY", defaults={"name": "SPY"})
    return idx


def _fmp_rows():
    # FMP /stable/historical-price-eod/full 형식(내림차순 반환 모사)
    return [
        {"date": "2023-08-09", "open": 450.0, "high": 452.0, "low": 449.0,
         "close": 451.2, "volume": 1000, "change": 1.2, "changePercent": 0.27},
        {"date": "2023-08-08", "open": 448.0, "high": 451.0, "low": 447.5,
         "close": 450.0, "volume": 1100, "change": 2.0, "changePercent": 0.44},
        {"date": "2023-08-07", "open": 447.0, "high": 449.0, "low": 446.0,
         "close": 448.0, "volume": 1200, "change": None, "changePercent": None},
    ]


def _run(rows, **kw):
    out = StringIO()
    opts = {"from": "2023-08-07", "to": "2023-08-09", **kw}
    with patch(
        "packages.shared.api_request.providers.fmp.client.FMPClient"
    ) as MockClient:
        MockClient.return_value.get_historical_price.return_value = rows
        call_command("backfill_spy_eod", stdout=out, stderr=out, **opts)
    return out.getvalue()


class TestBackfillSpyEod:
    def test_dry_run_writes_nothing(self, spy_index):
        from macro.models.indicators import MarketIndexPrice

        out = _run(_fmp_rows())  # --commit 미지정 = dry-run
        assert MarketIndexPrice.objects.count() == 0
        assert "DRY-RUN" in out
        assert "신규 삽입대상 3" in out

    def test_commit_inserts_then_idempotent(self, spy_index):
        from macro.models.indicators import MarketIndexPrice

        _run(_fmp_rows(), commit=True)
        assert MarketIndexPrice.objects.filter(index=spy_index).count() == 3
        # change=None 행도 삽입됨(close 존재)
        row = MarketIndexPrice.objects.get(index=spy_index, date=date(2023, 8, 7))
        from decimal import Decimal
        assert row.change is None and row.close == Decimal("448.0")
        # 재실행 → 추가 0(멱등)
        out2 = _run(_fmp_rows(), commit=True)
        assert MarketIndexPrice.objects.filter(index=spy_index).count() == 3
        assert "신규 삽입대상 0" in out2

    def test_window_filter_excludes_out_of_range(self, spy_index):
        from macro.models.indicators import MarketIndexPrice

        rows = _fmp_rows() + [
            {"date": "2022-01-01", "close": 400.0, "volume": 1},  # 창 밖
        ]
        _run(rows, commit=True)
        assert not MarketIndexPrice.objects.filter(date=date(2022, 1, 1)).exists()
        assert MarketIndexPrice.objects.count() == 3
