"""
Slice 19a — 목표-대비 권유 엔진 (정직한 A).

DECISIONS `SLICE19A`. 이 엔진은 수익 예측기가 아니다 — "목표-의식 + 신뢰도 기반 배치 코치".
갭은 forward 예측이 아니라 데이터가 받쳐주는 두 축으로 정의한다:
  - 진행 갭 = 현재 포트폴리오 실현/미실현 수익률(avg_cost vs 현재가) − 목표수익률 (후행·사실).
  - 배치 갭 = 유휴현금 비중(현금 / 총평가) (구조·사실).
통화별로 분리 계산한다(환전 없음 — 교차환전은 19b).

★ 금지: analyst_target_price·forward_pe·프리셋 스코어링 엔진 출력을 기대수익으로 쓰지 않는다
  (STEP0_SIGNAL_INVENTORY: 전부 유령/고아/후행). 없는 예측치를 프록시로 짓지 않는다.
"""

from __future__ import annotations

from decimal import Decimal

from apps.portfolio.models import WalletHolding
from apps.portfolio.models_my import CashBalance

# 매수 억제/발동 임계 — 19b에서 보정. 여기선 뼈대 자리표시.
IDLE_CASH_THRESHOLD = Decimal("0.10")  # 유휴현금 비중 10% 초과 → 매수 여력 있음


def _current_price(stock) -> Decimal:
    """현재가 = DailyPrice 최신 종가(실측 사실). 부재 시 real_time_price fallback.

    forward 추정이 아니라 관측된 가격만 사용(정직한-A).
    """
    from packages.shared.stocks.models import DailyPrice

    dp = (
        DailyPrice.objects.filter(stock=stock)
        .order_by("-date")
        .values_list("close_price", flat=True)
        .first()
    )
    if dp:
        return Decimal(dp)
    return Decimal(stock.real_time_price or 0)


def compute_progress_gap(user, goal) -> dict:
    """통화별 진행 갭 = (현재 미실현 수익률) − (목표수익률). 후행·사실.

    반환: {currency: {"return_pct", "gap_pct", "cost", "value"}}.
    """
    holdings = WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    by_cur: dict[str, list] = {}
    for h in holdings:
        cur = h.stock.currency
        cost = h.shares * h.avg_cost
        value = h.shares * _current_price(h.stock)
        acc = by_cur.setdefault(cur, [Decimal(0), Decimal(0)])
        acc[0] += cost
        acc[1] += value

    target = Decimal(goal.target_return_pct) if goal else Decimal(0)
    result = {}
    for cur, (cost, value) in by_cur.items():
        ret_pct = ((value - cost) / cost * 100) if cost else Decimal(0)
        result[cur] = {
            "return_pct": ret_pct,
            "gap_pct": ret_pct - target,  # 음수 = 목표 미달
            "cost": cost,
            "value": value,
        }
    return result


def compute_allocation_gap(user) -> dict:
    """통화별 배치 갭 = 유휴현금 비중(현금 / (현금+보유평가)). 구조·사실.

    반환: {currency: {"cash", "holdings_value", "idle_ratio"}}.
    """
    cash_by_cur: dict[str, Decimal] = {}
    for cb in CashBalance.objects.filter(wallet__user=user):
        cash_by_cur[cb.currency] = cash_by_cur.get(cb.currency, Decimal(0)) + cb.amount

    hold_by_cur: dict[str, Decimal] = {}
    holdings = WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    for h in holdings:
        cur = h.stock.currency
        hold_by_cur[cur] = hold_by_cur.get(cur, Decimal(0)) + h.shares * _current_price(h.stock)

    result = {}
    for cur in set(cash_by_cur) | set(hold_by_cur):
        cash = cash_by_cur.get(cur, Decimal(0))
        hold = hold_by_cur.get(cur, Decimal(0))
        total = cash + hold
        idle_ratio = (cash / total) if total else Decimal(1)
        result[cur] = {"cash": cash, "holdings_value": hold, "idle_ratio": idle_ratio}
    return result


def determine_mode(progress_gap: dict, allocation_gap: dict) -> str:
    """모드 분기: 어느 통화든 (유휴현금 임계 초과 OR 목표 미달) → BUY, 아니면 DEFEND.

    - BUY  = 매수 여력 있음(현금) 또는 목표 미달(더 굴려야) → 배치 권유
    - DEFEND = 완전투자 & 목표 달성 → 방어(HOLD/TRIM 중심)
    """
    idle_high = any(
        a["idle_ratio"] > IDLE_CASH_THRESHOLD for a in allocation_gap.values()
    )
    below_target = any(p["gap_pct"] < 0 for p in progress_gap.values())
    return "BUY" if (idle_high or below_target) else "DEFEND"
