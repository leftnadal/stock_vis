"""
metrics 앱 테스트 공통 fixtures
"""

from decimal import Decimal

import pytest
from django.core.management import call_command

from packages.shared.stocks.models import Stock


@pytest.fixture(autouse=True)
@pytest.mark.django_db
def seed_metrics():
    """모든 metrics 테스트 전에 시드 데이터 투입"""
    call_command('seed_metric_definitions', verbosity=0)


@pytest.fixture
@pytest.mark.django_db
def stock_aapl():
    return Stock.objects.create(
        symbol='AAPL',
        stock_name='Apple Inc.',
        sector='Technology',
        industry='Consumer Electronics',
        market_capitalization=Decimal('3000000000000'),
        pe_ratio=Decimal('28.5'),
    )


@pytest.fixture
@pytest.mark.django_db
def stock_msft():
    return Stock.objects.create(
        symbol='MSFT',
        stock_name='Microsoft Corporation',
        sector='Technology',
        industry='Software—Infrastructure',
        market_capitalization=Decimal('2800000000000'),
        pe_ratio=Decimal('32.1'),
    )


@pytest.fixture
@pytest.mark.django_db
def stock_googl():
    return Stock.objects.create(
        symbol='GOOGL',
        stock_name='Alphabet Inc.',
        sector='Technology',
        industry='Internet Content & Information',
        market_capitalization=Decimal('2000000000000'),
        pe_ratio=Decimal('25.0'),
    )
