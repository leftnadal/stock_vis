"""
Slice 19a — 정직한 A 권유 엔진 단위 테스트 (DECISIONS SLICE19A).

갭 2종·모드 분기·랭킹 키·가드레일·통화 분리·경계(빈 watchlist·현금0·목표 달성).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.services import advisory_engine as eng
from apps.portfolio.services import my_container as mc
from packages.shared.stocks.models import DailyPrice, Stock
from packages.shared.users.models import Watchlist, WatchlistItem

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="eng19a", password="x")


@pytest.fixture
def wallet(user):
    return Wallet.objects.create(user=user)


def _stock(symbol, currency="USD", price="100"):
    s = Stock.objects.create(symbol=symbol, currency=currency)
    p = Decimal(price)
    DailyPrice.objects.create(
        stock=s,
        date=date(2026, 7, 10),
        open_price=p,
        high_price=p,
        low_price=p,
        close_price=p,
        volume=1000,
    )
    return s


def _hold(wallet, stock, shares="10", avg_cost="100"):
    return WalletHolding.objects.create(
        wallet=wallet,
        stock=stock,
        shares=Decimal(shares),
        avg_cost=Decimal(avg_cost),
        first_bought_at=date(2026, 1, 1),
    )


# ---- 진행 갭 ----


@pytest.mark.django_db
def test_progress_gap_unrealized_return(user, wallet):
    stock = _stock("AAA", price="120")  # 100 → 120 = +20%
    _hold(wallet, stock, shares="10", avg_cost="100")
    goal = mc.upsert_goal_for_user(user, target_return_pct=Decimal("15"), horizon_months=12)

    gap = eng.compute_progress_gap(user, goal)
    # KRW 교정(SLICE19B): FX rate 미적재 시 1배 fallback → 수익률 보존, KRW 통합 구조
    assert gap["return_pct"] == Decimal("20")
    assert gap["gap_pct"] == Decimal("5")  # 20 − 15
    assert "USD" in gap["by_currency"]  # 통화별 소계 참고 유지


@pytest.mark.django_db
def test_progress_gap_below_target(user, wallet):
    stock = _stock("BBB", price="90")  # −10%
    _hold(wallet, stock, avg_cost="100")
    goal = mc.upsert_goal_for_user(user, target_return_pct=Decimal("10"), horizon_months=12)
    gap = eng.compute_progress_gap(user, goal)
    assert gap["gap_pct"] < 0  # KRW 통합 목표 미달


# ---- 배치 갭 + 모드 분기 ----


@pytest.mark.django_db
def test_allocation_gap_and_buy_mode_idle_cash(user, wallet):
    stock = _stock("CCC", price="100")
    _hold(wallet, stock, shares="1", avg_cost="100")  # 보유 100
    mc.upsert_cash_for_wallet(wallet, Decimal("900"), currency="USD")  # 현금 900

    alloc = eng.compute_allocation_gap(user)
    assert alloc["idle_ratio"] == Decimal("0.9")  # KRW 통합 900/1000

    goal = mc.upsert_goal_for_user(user, target_return_pct=Decimal("5"), horizon_months=12)
    progress = eng.compute_progress_gap(user, goal)
    # SLICE19C: determine_mode는 다이얼(deployable) 소비. 기본 손잡이 → 버퍼 10% 재현.
    dial = eng.compute_dial(user, alloc, goal)
    assert eng.determine_mode(progress, dial) == "BUY"  # 여력 존재(유휴현금 큼)


@pytest.mark.django_db
def test_defend_mode_full_invest_target_met(user, wallet):
    stock = _stock("DDD", price="130")  # +30%
    _hold(wallet, stock, shares="10", avg_cost="100")
    # 현금 없음 → 완전투자
    goal = mc.upsert_goal_for_user(user, target_return_pct=Decimal("10"), horizon_months=12)
    progress = eng.compute_progress_gap(user, goal)
    alloc = eng.compute_allocation_gap(user)
    # SLICE19C: 여력 0(현금 0 → deployable 0) & 목표 달성 → DEFEND.
    dial = eng.compute_dial(user, alloc, goal)
    assert eng.determine_mode(progress, dial) == "DEFEND"  # 목표 달성 & 여력 0


# ---- 가드레일 2: 집중도 TRIM ----


@pytest.mark.django_db
def test_trim_concentration(user, wallet):
    a = _stock("EEE", price="100")
    b = _stock("FFF", price="100")
    _hold(wallet, a, shares="8", avg_cost="100")  # 800 = 80%
    _hold(wallet, b, shares="2", avg_cost="100")  # 200 = 20%
    trims = eng.find_trim_candidates(user)
    symbols = {t["symbol"] for t in trims}
    assert "EEE" in symbols and "FFF" not in symbols  # 80% > 30% 임계


# ---- 랭킹 + 통화 분리 + 가드레일 1 ----


@pytest.mark.django_db
def test_rank_currency_separation_and_idle_guard(user, wallet):
    held = _stock("HELD", currency="USD", price="100")
    _hold(wallet, held, shares="1", avg_cost="100")  # USD 보유 100
    mc.upsert_cash_for_wallet(wallet, Decimal("900"), currency="USD")  # USD 여력

    # USD 후보 + KRW 후보
    cand_usd = _stock("CANDUSD", currency="USD", price="50")
    cand_krw = _stock("CANDKRW", currency="KRW", price="5000")
    wl = Watchlist.objects.create(user=user, name="wl")
    WatchlistItem.objects.create(watchlist=wl, stock=cand_usd)
    WatchlistItem.objects.create(watchlist=wl, stock=cand_krw)

    alloc = eng.compute_allocation_gap(user)
    ranked_usd = eng.rank_candidates(user, "USD", alloc)
    assert {c["symbol"] for c in ranked_usd} == {"CANDUSD"}  # KRW 후보 제외(통화 분리)

    # KRW 여력 없음 → 가드레일 1(빈 후보)
    assert eng.rank_candidates(user, "KRW", alloc) == []


# ---- 산출 계약 + 경계 ----


@pytest.mark.django_db
def test_recommend_contract_shape(user, wallet):
    held = _stock("GGG", currency="USD", price="100")
    _hold(wallet, held, shares="1", avg_cost="100")
    mc.upsert_cash_for_wallet(wallet, Decimal("900"), currency="USD")
    mc.upsert_goal_for_user(user, target_return_pct=Decimal("50"), horizon_months=12)
    wl = Watchlist.objects.create(user=user, name="wl")
    WatchlistItem.objects.create(watchlist=wl, stock=_stock("CAND", currency="USD", price="50"))

    out = eng.recommend(user)
    assert out["mode"] == "BUY"
    assert set(out["summary"]) == {"progress_gap", "allocation_gap", "goal_target_return_pct", "numeraire", "cost_basis_note", "fx_context"}
    actions = {r["action"] for r in out["recommendations"]}
    assert actions <= {"BUY", "HOLD", "TRIM"}
    assert "BUY" in actions and "HOLD" in actions  # 후보 매수 + 보유 유지
    assert "예측" in out["disclaimer"]  # 예측-아님 명시
    for r in out["recommendations"]:
        assert set(r) == {"action", "symbol", "currency", "score", "rationale"}


@pytest.mark.django_db
def test_recommend_empty_watchlist_and_zero_cash(user, wallet):
    held = _stock("HHH", currency="USD", price="120")
    _hold(wallet, held, shares="10", avg_cost="100")  # +20%, 현금0, watchlist 없음
    mc.upsert_goal_for_user(user, target_return_pct=Decimal("10"), horizon_months=12)

    out = eng.recommend(user)
    # 완전투자 & 목표 달성 → DEFEND, BUY 후보 없음(빈 watchlist·현금0 경계)
    assert out["mode"] == "DEFEND"
    assert all(r["action"] != "BUY" for r in out["recommendations"])
    # 단일 보유(현금0)는 총배치 100% → TRIM. BUY만 없으면 경계 통과.
    assert out["recommendations"]  # 최소 TRIM/HOLD 존재
