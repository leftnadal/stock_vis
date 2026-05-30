"""
Users 앱 테스트 공통 fixtures
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from packages.shared.stocks.models import Stock

User = get_user_model()


@pytest.fixture
def api_client():
    """API Client fixture"""
    return APIClient()


@pytest.fixture
@pytest.mark.django_db
def authenticated_user():
    """인증된 사용자"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        nick_name='테스트유저',
    )


@pytest.fixture
@pytest.mark.django_db
def other_user():
    """다른 사용자 (권한 테스트용)"""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpass123',
        nick_name='다른유저',
    )


@pytest.fixture
@pytest.mark.django_db
def stock_aapl():
    """AAPL Stock fixture"""
    return Stock.objects.create(
        symbol='AAPL',
        stock_name='Apple Inc.',
        sector='Technology',
        industry='Consumer Electronics',
        exchange='NASDAQ',
        currency='USD',
        market_capitalization=Decimal('2500000000000'),
        real_time_price=Decimal('150.25'),
    )


@pytest.fixture
@pytest.mark.django_db
def stock_msft():
    """MSFT Stock fixture"""
    return Stock.objects.create(
        symbol='MSFT',
        stock_name='Microsoft Corporation',
        sector='Technology',
        industry='Software',
        exchange='NASDAQ',
        currency='USD',
        market_capitalization=Decimal('2800000000000'),
        real_time_price=Decimal('375.50'),
    )


@pytest.fixture
@pytest.mark.django_db
def portfolio(authenticated_user, stock_aapl):
    """기본 Portfolio fixture"""
    from packages.shared.users.models import Portfolio

    return Portfolio.objects.create(
        user=authenticated_user,
        stock=stock_aapl,
        quantity=Decimal('10'),
        average_price=Decimal('140.00'),
        target_price=Decimal('180.00'),
        stop_loss_price=Decimal('120.00'),
        notes='장기 보유',
    )
