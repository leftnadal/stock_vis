"""A-S0 — cleanup_old_data 보존 예외(SPY) 회귀.

계약: 롤링 365일 purge가 PRESERVED_INDEX_SYMBOLS(SPY)의 오래된 EOD는 건너뛰고,
  비보존 심볼의 오래된 EOD는 기존대로 삭제한다(행위보존 = 비보존 심볼 purge 불변).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.market_pulse.tasks.macro import PRESERVED_INDEX_SYMBOLS, cleanup_old_data

pytestmark = [pytest.mark.django_db]


@pytest.fixture(autouse=True)
def _clean():
    from macro.models.indicators import IndicatorValue, MarketIndexPrice

    MarketIndexPrice.objects.all().delete()
    IndicatorValue.objects.all().delete()
    yield


def _mk_index(symbol):
    from macro.models.indicators import MarketIndex

    idx, _ = MarketIndex.objects.get_or_create(symbol=symbol, defaults={"name": symbol})
    return idx


def _mk_price(idx, d):
    from macro.models.indicators import MarketIndexPrice

    MarketIndexPrice.objects.create(index=idx, date=d, close=Decimal("100"))


class TestCleanupPreservation:
    def test_spy_old_survives_others_purged(self):
        from macro.models.indicators import MarketIndexPrice

        old = date.today() - timedelta(days=400)  # 365 초과 → purge 대상
        recent = date.today() - timedelta(days=10)  # 유지
        spy = _mk_index("SPY")
        xlf = _mk_index("XLF")  # 비보존
        for idx in (spy, xlf):
            _mk_price(idx, old)
            _mk_price(idx, recent)

        cleanup_old_data.run()

        # SPY: old + recent 둘 다 생존(보존 예외)
        assert MarketIndexPrice.objects.filter(index=spy, date=old).exists()
        assert MarketIndexPrice.objects.filter(index=spy, date=recent).exists()
        # XLF: old 삭제(행위보존 = 비보존 심볼 purge 불변), recent 생존
        assert not MarketIndexPrice.objects.filter(index=xlf, date=old).exists()
        assert MarketIndexPrice.objects.filter(index=xlf, date=recent).exists()

    def test_preserved_set_contains_spy(self):
        assert "SPY" in PRESERVED_INDEX_SYMBOLS

    def test_indicator_purge_unchanged(self):
        # 행위보존: IndicatorValue purge는 이 슬라이스에서 무변경(365일 컷 유지).
        from macro.models.indicators import EconomicIndicator, IndicatorValue

        ind, _ = EconomicIndicator.objects.get_or_create(
            code="NFCI", defaults={"name": "NFCI", "category": "macro", "data_source": "fred"}
        )
        old = date.today() - timedelta(days=400)
        IndicatorValue.objects.create(indicator=ind, date=old, value=Decimal("0.1"))
        cleanup_old_data.run()
        assert not IndicatorValue.objects.filter(indicator=ind, date=old).exists()
