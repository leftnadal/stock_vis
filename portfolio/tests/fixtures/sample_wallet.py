"""
Django DB 기반 Wallet/WalletHolding 생성 헬퍼.

pytest-django `@pytest.mark.django_db` 환경에서 호출.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from portfolio.models import Wallet, WalletHolding


def _get_or_create_user(username: str = "test-user"):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username)
    return user


def create_tech_wallet(username: str = "test-user") -> Wallet:
    """Tech 5종목 보유 Wallet 생성 (Stock FK는 미리 존재해야 함)."""
    from stocks.models import Stock

    user = _get_or_create_user(username)
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={"name": "Test Wallet"})

    for sym, name, avg_cost, shares in [
        ("NVDA",  "NVIDIA Corporation",   "90.00", "10"),
        ("MSFT",  "Microsoft Corp",       "340.00", "8"),
        ("AAPL",  "Apple Inc",            "180.00", "10"),
        ("GOOGL", "Alphabet Inc",         "130.00", "12"),
        ("INTC",  "Intel Corporation",    "48.00", "20"),
    ]:
        stock, _ = Stock.objects.get_or_create(
            symbol=sym,
            defaults={
                "stock_name": name,
                "sector": "Technology",
                "industry": "Semiconductors" if sym in {"NVDA", "AMD", "INTC"} else "Software",
            },
        )
        WalletHolding.objects.get_or_create(
            wallet=wallet, stock=stock,
            defaults={
                "shares": Decimal(shares),
                "avg_cost": Decimal(avg_cost),
                "first_bought_at": date(2025, 6, 1),
                "investment_thesis": "",
            },
        )

    return wallet
