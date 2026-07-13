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
CONCENTRATION_THRESHOLD = Decimal("0.30")  # 한 종목 통화별 30% 초과 → TRIM 후보


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


# ============================================================
# 후보 랭킹 (B-min) — RelationConfidence(주) + 진입가 여유(부). 가중치 없음(19b).
# ============================================================


def _relation_score(candidate_symbol, holding_symbols) -> float:
    """후보 심볼이 보유 심볼(seed)과 연결된 최대 RelationConfidence.truth_score.

    해자(관계 신뢰도)를 랭킹 키로 재사용. dashboard strip_service와 동일 소스.
    연결 없으면 0.0.
    """
    if not holding_symbols:
        return 0.0
    from django.db.models import Q

    from apps.chain_sight.models.relation_discovery import RelationConfidence

    scores = RelationConfidence.objects.filter(
        Q(symbol_a=candidate_symbol, symbol_b__in=holding_symbols)
        | Q(symbol_b=candidate_symbol, symbol_a__in=holding_symbols)
    ).values_list("truth_score", flat=True)
    return max(scores, default=0.0)


def rank_candidates(user, currency, allocation_gap) -> list:
    """매수 모드 후보 정렬. 통화별 매수여력 게이트(가드레일 1) + 통화 분리.

    정렬 키: RelationConfidence(주, 내림) → distance_from_entry(부, 오름=목표가 아래 우선).
    가중치 없음(단순 정렬) — 19b에서 가중 스코어로 교체.
    """
    from packages.shared.users.models import WatchlistItem

    alloc = allocation_gap.get(currency)
    # 가드레일 1: 유휴현금 임계 미만 → 매수 억제(빈 후보)
    if alloc is None or alloc["idle_ratio"] < IDLE_CASH_THRESHOLD:
        return []

    holdings = WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    holding_symbols = [h.stock.symbol for h in holdings if h.stock.currency == currency]

    candidates = WatchlistItem.objects.filter(
        watchlist__user=user
    ).select_related("stock")

    ranked = []
    for wi in candidates:
        if wi.stock.currency != currency:  # 통화 분리 (환전 없음)
            continue
        ranked.append(
            {
                "symbol": wi.stock.symbol,
                "currency": currency,
                "relation_score": _relation_score(wi.stock.symbol, holding_symbols),
                "distance_from_entry": wi.distance_from_entry,  # None 가능
            }
        )

    ranked.sort(
        key=lambda x: (
            -x["relation_score"],
            x["distance_from_entry"] if x["distance_from_entry"] is not None else 0.0,
        )
    )
    return ranked


def find_trim_candidates(user) -> list:
    """가드레일 2: 통화별 집중도 초과 보유 → TRIM 후보.

    비중 = 종목 평가액 / (해당 통화 총 보유평가). 임계 초과 시 TRIM.
    """
    holdings = list(
        WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    )
    valued = [(h, h.shares * _current_price(h.stock)) for h in holdings]

    # 집중도 분모 = 통화별 총 배치(보유평가 + 현금). 현금 많으면 종목 집중 완화(정직).
    total_by_cur: dict[str, Decimal] = {}
    for h, v in valued:
        cur = h.stock.currency
        total_by_cur[cur] = total_by_cur.get(cur, Decimal(0)) + v
    for cb in CashBalance.objects.filter(wallet__user=user):
        total_by_cur[cb.currency] = total_by_cur.get(cb.currency, Decimal(0)) + cb.amount

    trims = []
    for h, v in valued:
        cur = h.stock.currency
        total = total_by_cur[cur]
        weight = (v / total) if total else Decimal(0)
        if weight > CONCENTRATION_THRESHOLD:
            trims.append(
                {"symbol": h.stock.symbol, "currency": cur, "weight": weight}
            )
    return trims


# ============================================================
# 산출 계약 (D4) — Slice 20이 소비하는 안정 형태
# ============================================================

DISCLAIMER = (
    "19a는 수익 예측기가 아닙니다 — 목표-의식·신뢰도/여력 기반 배치 코치. "
    "갭은 후행(현재 수익률)·구조(유휴현금) 사실이며 forward 예측이 아닙니다."
)


def recommend(user) -> dict:
    """목표-대비 권유 산출(계약). action ∈ {BUY, HOLD, TRIM}.

    반환:
      {
        "mode": "BUY"|"DEFEND",
        "summary": {progress_gap(통화별), allocation_gap(통화별), goal_target_return_pct},
        "recommendations": [{action, symbol, currency, score, rationale}, ...],
        "disclaimer": "...예측 아님...",
      }
    """
    from apps.portfolio.services.my_container import get_goal_for_user

    goal = get_goal_for_user(user)
    progress = compute_progress_gap(user, goal)
    allocation = compute_allocation_gap(user)
    mode = determine_mode(progress, allocation)

    recommendations = []

    # 가드레일 2: TRIM (집중도 초과, 모드 무관 항상 검사)
    trim_symbols = set()
    for t in find_trim_candidates(user):
        trim_symbols.add(t["symbol"])
        recommendations.append(
            {
                "action": "TRIM",
                "symbol": t["symbol"],
                "currency": t["currency"],
                "score": None,
                "rationale": (
                    f"통화별 집중도 {t['weight'] * 100:.0f}% > "
                    f"{CONCENTRATION_THRESHOLD * 100:.0f}% — 배치 규칙(예측 아님)"
                ),
            }
        )

    # HOLD: 보유 중 TRIM 아닌 것 (현재 포지션 유지)
    holdings = WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    for h in holdings:
        if h.stock.symbol not in trim_symbols:
            recommendations.append(
                {
                    "action": "HOLD",
                    "symbol": h.stock.symbol,
                    "currency": h.stock.currency,
                    "score": None,
                    "rationale": "집중도 정상 — 보유 유지",
                }
            )

    # BUY: 매수 모드 & 통화별 여력 있는 후보 (RelationConfidence+진입가 정렬)
    if mode == "BUY":
        for currency in allocation:
            for c in rank_candidates(user, currency, allocation):
                dist = c["distance_from_entry"]
                dist_txt = f"진입가 여유 {dist:.1f}%" if dist is not None else "진입가 미설정"
                recommendations.append(
                    {
                        "action": "BUY",
                        "symbol": c["symbol"],
                        "currency": currency,
                        "score": c["relation_score"],
                        "rationale": (
                            f"관계 신뢰도 {c['relation_score']:.2f}, {dist_txt} "
                            "— 신뢰도/여력 기반(예측 아님)"
                        ),
                    }
                )

    return {
        "mode": mode,
        "summary": {
            "progress_gap": progress,
            "allocation_gap": allocation,
            "goal_target_return_pct": (
                goal.target_return_pct if goal else None
            ),
        },
        "recommendations": recommendations,
        "disclaimer": DISCLAIMER,
    }
