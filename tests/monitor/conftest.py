"""Monitor 테스트 공용 픽스처 (MON-P2-S2)."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.monitor.models import IndicatorReading, Monitor, MonitorIndicator

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="mon_engine_user", password="pw12345")


@pytest.fixture
def monitor(user):
    return Monitor.objects.create(
        user=user, scope=Monitor.Scope.STOCK, target_ref="AAPL", name="애플 감시"
    )


@pytest.fixture
def make_indicator(monitor):
    def _make(**kwargs):
        defaults = dict(
            monitor=monitor,
            name="지표",
            indicator_type=MonitorIndicator.IndicatorType.MARKET_DATA,
            support_direction=MonitorIndicator.SupportDirection.POSITIVE,
            weight=1.0,
        )
        defaults.update(kwargs)
        return MonitorIndicator.objects.create(**defaults)

    return _make


@pytest.fixture
def add_readings():
    """지표에 시계열 판독값 추가 (오늘 기준 역순 일자)."""

    def _add(indicator, values, status="ok"):
        base = timezone.now()
        n = len(values)
        for i, v in enumerate(values):
            IndicatorReading.objects.create(
                indicator=indicator,
                value=v,
                asof=base - timedelta(days=(n - 1 - i)),
                validation_status=status,
            )

    return _add
