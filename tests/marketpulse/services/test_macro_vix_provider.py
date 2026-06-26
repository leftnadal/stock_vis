"""MacroVIXProvider DB 쿼리 단위 테스트 — IndicatorValue(VIXCLS) 소스.

VIX price 소스를 macro.MarketIndex/MarketIndexPrice(volatility, 현재 0건)에서
macro.IndicatorValue(code='VIXCLS', 232행 적재)로 교체한 동작을 검증한다.
포트 계약(list[Decimal] 날짜 오름차순 / 최신 float|None)은 불변.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.market_pulse.services.macro_vix_provider import MacroVIXProvider

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def vixcls_rows():
    """VIXCLS 지표 + 4개 관측치(주말 건너뜀 포함)."""
    from macro.models import EconomicIndicator, IndicatorValue

    ind = EconomicIndicator.objects.create(
        code="VIXCLS",
        name="CBOE Volatility Index",
        category="volatility",
        data_source="fred",
    )
    rows = {
        date(2026, 3, 11): Decimal("18.50"),
        date(2026, 3, 12): Decimal("20.10"),
        date(2026, 3, 13): Decimal("27.19"),  # 고변동 스폿
        date(2026, 3, 16): Decimal("22.40"),  # 월요일(주말 건너뜀)
    }
    for d, v in rows.items():
        IndicatorValue.objects.create(indicator=ind, date=d, value=v)
    return rows


class TestGetVixSeries:
    def test_returns_decimal_list_ascending(self, vixcls_rows):
        p = MacroVIXProvider()
        result = p.get_vix_series(date(2026, 3, 10), date(2026, 3, 16))
        assert result == [
            Decimal("18.50"),
            Decimal("20.10"),
            Decimal("27.19"),
            Decimal("22.40"),
        ]
        assert all(isinstance(x, Decimal) for x in result)

    def test_date_from_exclusive_date_to_inclusive(self, vixcls_rows):
        """포트 계약: date_from < date <= date_to."""
        p = MacroVIXProvider()
        result = p.get_vix_series(date(2026, 3, 11), date(2026, 3, 13))
        # 3/11 제외(exclusive), 3/13 포함(inclusive)
        assert result == [Decimal("20.10"), Decimal("27.19")]

    def test_empty_list_when_no_indicator(self, db):
        p = MacroVIXProvider()
        assert p.get_vix_series(date(2026, 1, 1), date(2026, 12, 31)) == []


class TestGetLatestVix:
    def test_returns_float_latest_on_or_before(self, vixcls_rows):
        p = MacroVIXProvider()
        val = p.get_latest_vix(date(2026, 3, 13))
        assert val == 27.19
        assert isinstance(val, float)

    def test_uses_lte_target_when_exact_missing(self, vixcls_rows):
        """3/14·3/15 결측 → 3/13이 최신."""
        p = MacroVIXProvider()
        assert p.get_latest_vix(date(2026, 3, 15)) == 27.19

    def test_none_when_no_data(self, db):
        p = MacroVIXProvider()
        assert p.get_latest_vix(date(2026, 3, 13)) is None
