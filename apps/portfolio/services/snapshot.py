"""
Slice 19c — 자산 스냅샷 파이프라인 + 드로다운(dd) 계산.

DECISIONS `SLICE19C`. 두 책임을 격리한다:
  1. 평가 스냅샷 생성/upsert(`evaluate_portfolio`, `upsert_snapshot`) — 엔진 실행 + nightly.
  2. flow 조정 드로다운(`compute_drawdown`) — 입출금 오염 차단(가격효과만 누적).

★ 정직성: dd는 **가격·환율 효과만**(flow 분해). 입출금은 성과가 아니므로 dd에서 배제.
   환율 하락은 KRW 평가 감소로 dd에 **자동 반영**(emergent, 별도 FX 예측 없음).

의존 방향: snapshot → advisory_engine(평가 헬퍼 재사용). advisory_engine은 이 모듈을
lazy-import(순환 회피). apps→shared 단방향 유지.
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.portfolio.models import WalletHolding
from apps.portfolio.models_my import CashBalance, PortfolioSnapshot
from apps.portfolio.services.advisory_engine import _current_price, _krw_rate

# 가격 신선도: 보유 가격 나이 > 영업일 2일 → dd 동결
STALE_PRICE_BDAYS = 2


def _business_days(d_from: date_cls, d_to: date_cls) -> int:
    """d_from(제외) ~ d_to(포함) 사이 영업일(월~금) 수. d_to<=d_from이면 0."""
    if d_to <= d_from:
        return 0
    days, d = 0, d_from
    while d < d_to:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


# ============================================================
# 1. 평가 + 스냅샷 upsert
# ============================================================


def evaluate_portfolio(user) -> dict:
    """현재 보유+현금의 KRW 평가(사실). advisory_engine 평가경로 재사용(REUSE_WIRING).

    반환: {total_krw, by_currency, holdings_detail, price_as_of}.
    - by_currency/holdings_detail 수치는 JSON 저장 위해 str 직렬화.
    - price_as_of = 보유 종목 최신 DailyPrice.date 중 **가장 오래된 것**(보수적 신선도).
    """
    from packages.shared.stocks.models import DailyPrice

    holdings = WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    by_cur: dict[str, dict] = {}
    detail: list[dict] = []
    total = Decimal(0)
    price_dates: list[date_cls] = []

    for h in holdings:
        cur = h.stock.currency
        rate = _krw_rate(cur)
        price = _current_price(h.stock)
        value_krw = h.shares * price * rate
        total += value_krw
        slot = by_cur.setdefault(cur, {"holdings_krw": Decimal(0), "cash_krw": Decimal(0)})
        slot["holdings_krw"] += value_krw
        detail.append(
            {
                "symbol": h.stock.symbol,
                "currency": cur,
                "shares": str(h.shares),
                "price": str(price),
                "fx_rate": str(rate),
                "value_krw": str(value_krw),
            }
        )
        d = (
            DailyPrice.objects.filter(stock=h.stock)
            .order_by("-date")
            .values_list("date", flat=True)
            .first()
        )
        if d:
            price_dates.append(d)

    for cb in CashBalance.objects.filter(wallet__user=user):
        rate = _krw_rate(cb.currency)
        v = cb.amount * rate
        total += v
        slot = by_cur.setdefault(cb.currency, {"holdings_krw": Decimal(0), "cash_krw": Decimal(0)})
        slot["cash_krw"] += v

    return {
        "total_krw": total,
        "by_currency": {
            c: {"holdings_krw": str(v["holdings_krw"]), "cash_krw": str(v["cash_krw"])}
            for c, v in by_cur.items()
        },
        "holdings_detail": detail,
        "price_as_of": min(price_dates) if price_dates else None,
    }


def _flow_residual(prev: PortfolioSnapshot | None, ev: dict) -> Decimal:
    """플로우효과 = (총자산_now − 총자산_prev) − 가격효과.

    가격효과 = Σ(연속 보유 종목) prev_shares × (now_price_krw − prev_price_krw).
    (전일 수량 고정 × 가격·환율 변화). 매수/매도/현금이동 = 잔차 = flow.
    prev 없으면(콜드 스타트) flow 0.
    """
    if prev is None:
        return Decimal(0)
    prev_detail = {d["symbol"]: d for d in prev.holdings_detail}
    now_detail = {d["symbol"]: d for d in ev["holdings_detail"]}
    price_effect = Decimal(0)
    for sym, pd in prev_detail.items():
        nd = now_detail.get(sym)
        if nd is None:  # 매도 = flow (가격효과 아님)
            continue
        prev_shares = Decimal(pd["shares"])
        prev_price_krw = Decimal(pd["price"]) * Decimal(pd["fx_rate"])
        now_price_krw = Decimal(nd["price"]) * Decimal(nd["fx_rate"])
        price_effect += prev_shares * (now_price_krw - prev_price_krw)
    return (ev["total_krw"] - prev.total_krw) - price_effect


def upsert_snapshot(user, as_of: date_cls | None = None) -> PortfolioSnapshot:
    """평가 스냅샷 upsert(unique(user, date)). 엔진 실행 + nightly 이중 기록.

    net_flow_krw = 직전 스냅샷(date<as_of) 대비 flow 잔차.
    """
    if as_of is None:
        as_of = timezone.now().date()
    ev = evaluate_portfolio(user)
    prev = (
        PortfolioSnapshot.objects.filter(user=user, date__lt=as_of)
        .order_by("-date")
        .first()
    )
    net_flow = _flow_residual(prev, ev)
    snap, _ = PortfolioSnapshot.objects.update_or_create(
        user=user,
        date=as_of,
        defaults={
            "total_krw": ev["total_krw"],
            "by_currency": ev["by_currency"],
            "holdings_detail": ev["holdings_detail"],
            "net_flow_krw": net_flow,
            "price_as_of": ev["price_as_of"],
        },
    )
    return snap


# ============================================================
# 2. flow 조정 드로다운 (dd)
# ============================================================


def _is_stale(snap: PortfolioSnapshot) -> bool:
    """스냅샷 가격이 신선도 밖(> 영업일 2일)인가."""
    if snap.price_as_of is None:
        return True
    return _business_days(snap.price_as_of, snap.date) > STALE_PRICE_BDAYS


def compute_drawdown(user) -> dict:
    """flow 조정 드로다운. 고점 = UserGoal 스코프 관측 최대(목표 생성/변경 시 리셋).

    dd = max(0, (조정 고점 − 현재 총자산)/조정 고점). 조정 고점 = 고점 + 고점 이후 순입금.
    가격 신선도 밖이면 dd만 직전 유효(fresh) 스냅샷 값으로 동결.

    반환: {dd, is_new_high, peak, adjusted_peak, current_total, peak_date,
           window_days, frozen, available}.
    """
    from apps.portfolio.services.my_container import get_goal_for_user

    goal = get_goal_for_user(user)
    qs = PortfolioSnapshot.objects.filter(user=user)
    if goal is not None:
        qs = qs.filter(date__gte=goal.updated_at.date())  # 목표 변경 시 리셋(스코프)
    snaps = list(qs.order_by("date"))
    if not snaps:
        return {
            "available": False,
            "dd": Decimal(0),
            "is_new_high": True,
            "window_days": 0,
            "frozen": False,
        }

    latest = snaps[-1]
    frozen = _is_stale(latest)
    fresh = [s for s in snaps if not _is_stale(s)]
    cur = fresh[-1] if (frozen and fresh) else latest  # 동결: 직전 유효값

    window = [s for s in snaps if s.date <= cur.date]
    peak_snap = max(window, key=lambda s: s.total_krw)
    peak = peak_snap.total_krw
    inflow_since_peak = sum(
        (s.net_flow_krw for s in window if s.date > peak_snap.date), Decimal(0)
    )
    adjusted_peak = peak + inflow_since_peak
    current_total = cur.total_krw

    if adjusted_peak > 0:
        dd = (adjusted_peak - current_total) / adjusted_peak
        if dd < 0:
            dd = Decimal(0)
    else:
        dd = Decimal(0)

    return {
        "available": True,
        "dd": dd,  # 0~1 비율
        "is_new_high": current_total >= adjusted_peak,
        "peak": peak,
        "adjusted_peak": adjusted_peak,
        "current_total": current_total,
        "peak_date": peak_snap.date,
        "window_days": (cur.date - snaps[0].date).days + 1,
        "frozen": frozen,
    }
