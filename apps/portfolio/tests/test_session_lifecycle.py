"""D-8 Session lifecycle tests — 실제 Django DB 사용."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolio.models import (
    AnalysisRun,
    ChatSession,
    Decision,
    Message,
    Portfolio,
    Wallet,
    WalletHolding,
)
from packages.shared.stocks.models import Stock


@pytest.mark.django_db
def test_full_session_lifecycle():
    """Wallet → WalletHolding → Portfolio → AnalysisRun → ChatSession → Message → Decision 체인."""
    User = get_user_model()
    user = User.objects.create_user(username="lifecycle-user")
    wallet = Wallet.objects.create(user=user, name="Test Wallet")

    stock_nvda, _ = Stock.objects.get_or_create(
        symbol="NVDA",
        defaults={"stock_name": "NVIDIA", "sector": "Technology"},
    )
    stock_msft, _ = Stock.objects.get_or_create(
        symbol="MSFT",
        defaults={"stock_name": "Microsoft", "sector": "Technology"},
    )
    h1 = WalletHolding.objects.create(
        wallet=wallet,
        stock=stock_nvda,
        shares=Decimal("10"),
        avg_cost=Decimal("90.00"),
        first_bought_at=date(2025, 6, 1),
    )
    h2 = WalletHolding.objects.create(
        wallet=wallet,
        stock=stock_msft,
        shares=Decimal("8"),
        avg_cost=Decimal("340.00"),
        first_bought_at=date(2025, 6, 1),
    )

    portfolio = Portfolio.objects.create(
        wallet=wallet,
        name="Tech",
        wallet_holding_ids=[str(h1.id), str(h2.id)],
        save_type="named",
    )
    assert portfolio.effective_holdings().count() == 2

    run = AnalysisRun.objects.create(
        portfolio=portfolio,
        preset_id="garp",
        portfolio_hash="abc123",
    )
    session = ChatSession.objects.create(user=user, analysis_run=run)
    Message.objects.create(session=session, role="user", content="질문1")
    Message.objects.create(session=session, role="assistant", content="응답1")

    Decision.objects.create(
        user=user,
        decision_type="preset_adjustment",
        decision_at=datetime.now(timezone.utc),
        context_analysis_run=run,
        rationale_text="ROIC 상향 원함",
        structured_payload={"metric_id": "roic", "new_threshold": 0.20},
    )

    assert wallet.holdings.count() == 2
    assert session.messages.count() == 2
    assert Decision.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_portfolio_effective_holdings_after_sell():
    """H3 정책: Wallet에서 종목 제거 시 effective_holdings에서 자동 제외."""
    User = get_user_model()
    user = User.objects.create_user(username="h3-user")
    wallet = Wallet.objects.create(user=user, name="W")

    stocks_added = []
    holding_ids = []
    for sym in ("AAA", "BBB", "CCC"):
        stock, _ = Stock.objects.get_or_create(
            symbol=sym,
            defaults={"stock_name": sym, "sector": "Tech"},
        )
        stocks_added.append(stock)
        h = WalletHolding.objects.create(
            wallet=wallet,
            stock=stock,
            shares=Decimal("1"),
            avg_cost=Decimal("10"),
            first_bought_at=date(2025, 1, 1),
        )
        holding_ids.append(str(h.id))

    portfolio = Portfolio.objects.create(
        wallet=wallet,
        name="P",
        wallet_holding_ids=holding_ids,
        save_type="named",
    )
    assert portfolio.effective_holdings().count() == 3

    # 매도 시뮬레이션: 1개 삭제
    WalletHolding.objects.get(wallet=wallet, stock=stocks_added[0]).delete()

    assert portfolio.effective_holdings().count() == 2
    # Portfolio 정의는 변하지 않음
    portfolio.refresh_from_db()
    assert len(portfolio.wallet_holding_ids) == 3
