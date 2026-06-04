"""VIXProvider 포트 계약 단위 테스트."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from packages.shared.stocks.services import vix_provider as vp
from packages.shared.stocks.services.vix_provider import (
    VIXProvider,
    VIXProviderNotRegistered,
    get_vix_provider,
    register_vix_provider,
)


class _FakeProvider(VIXProvider):
    def __init__(self, latest=None, series=None):
        self._latest = latest
        self._series = series or []

    def get_latest_vix(self, target_date):
        return self._latest

    def get_vix_series(self, date_from, date_to):
        return self._series


@pytest.fixture(autouse=True)
def _reset_provider():
    """각 테스트 사이에 모듈 전역 _provider를 격리한다."""
    original = vp._provider
    vp._provider = None
    yield
    vp._provider = original


class TestRegistry:
    def test_get_without_register_raises(self):
        with pytest.raises(VIXProviderNotRegistered):
            get_vix_provider()

    def test_register_then_get_returns_same_instance(self):
        impl = _FakeProvider(latest=18.5)
        register_vix_provider(impl)
        assert get_vix_provider() is impl

    def test_register_is_idempotent_last_wins(self):
        a = _FakeProvider(latest=1.0)
        b = _FakeProvider(latest=2.0)
        register_vix_provider(a)
        register_vix_provider(b)
        assert get_vix_provider() is b


class TestPortContract:
    def test_latest_vix_returns_float_or_none(self):
        register_vix_provider(_FakeProvider(latest=22.7))
        assert get_vix_provider().get_latest_vix(date(2026, 6, 4)) == 22.7

        register_vix_provider(_FakeProvider(latest=None))
        assert get_vix_provider().get_latest_vix(date(2026, 6, 4)) is None

    def test_series_returns_decimal_list_ascending(self):
        series = [Decimal("15.1"), Decimal("16.0"), Decimal("17.3")]
        register_vix_provider(_FakeProvider(series=series))
        result = get_vix_provider().get_vix_series(
            date(2026, 3, 1), date(2026, 6, 4)
        )
        assert result == series
        assert all(isinstance(p, Decimal) for p in result)

    def test_abstract_methods_required(self):
        """VIXProvider는 ABC — 메서드 미구현 시 인스턴스화 불가."""
        with pytest.raises(TypeError):
            VIXProvider()  # type: ignore[abstract]


pytestmark = pytest.mark.unit
