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


def _krw_rate(currency: str) -> Decimal:
    """통화→KRW 환산 rate. KRW=1, USD=현재 spot. spot 부재 시 1(교정 불가 명시는 상위).

    SLICE19B: numéraire=KRW. USD 자산을 현재 환율로 KRW 평가.
    """
    if currency == "KRW":
        return Decimal(1)
    from packages.shared.fx.services import get_spot_rate

    spot = get_spot_rate("USDKRW")
    return spot if spot is not None else Decimal(1)


def krw_cost_basis(holding) -> tuple[Decimal, str]:
    """보유의 KRW 취득원가 + 출처 라벨 (게이트1 우선순위 로직, SLICE19B_GATE1_RESOLUTION §1).

    우선순위: exact(acquisition_fx_rate) > approx_first_buy(매수일 환율)
             > approx_low_confidence(창 밖 = 가장 오래된 환율) > native_krw.
    """
    usd_cost = holding.shares * holding.avg_cost  # 종목 통화 단위 원가

    if holding.stock.currency == "KRW":
        return usd_cost, "native_krw"

    # 1. exact — 사용자 캡처/정정값
    if holding.acquisition_fx_rate is not None:
        return usd_cost * holding.acquisition_fx_rate, "exact"

    from packages.shared.fx.services import get_rate_on, oldest_available

    # 2. approx_first_buy — 매수일(휴장일이면 직전 영업일) 환율
    rate = get_rate_on(holding.first_bought_at, "USDKRW")
    if rate is not None:
        return usd_cost * rate, "approx_first_buy"

    # 3. approx_low_confidence — 백필 창 밖 → 가장 오래된 가용 환율
    oldest = oldest_available("USDKRW")
    if oldest is not None:
        return usd_cost * oldest, "approx_low_confidence"

    # 환율 데이터 전무 — 원가 통화 그대로(상위에서 근사 명시)
    return usd_cost, "approx_low_confidence"


def compute_progress_gap(user, goal) -> dict:
    """진행 갭 = KRW 기준 포트폴리오 미실현 수익률 − 목표수익률 (후행·사실).

    numéraire=KRW(SLICE19B). USD 자산은 현재 환율로 KRW 평가, 원가는 취득원가 우선순위.
    통화별 소계(by_currency)는 참고 유지, 갭·모드 정본은 KRW 통합.
    반환: {"return_pct","gap_pct","cost_krw","value_krw","by_currency","cost_labels"}.
    """
    holdings = WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    total_cost_krw, total_value_krw = Decimal(0), Decimal(0)
    by_cur: dict[str, list] = {}
    labels: dict[str, int] = {}

    for h in holdings:
        cur = h.stock.currency
        rate = _krw_rate(cur)
        cost_krw, label = krw_cost_basis(h)
        value_krw = h.shares * _current_price(h.stock) * rate
        total_cost_krw += cost_krw
        total_value_krw += value_krw
        labels[label] = labels.get(label, 0) + 1
        acc = by_cur.setdefault(cur, [Decimal(0), Decimal(0)])
        acc[0] += cost_krw
        acc[1] += value_krw

    target = Decimal(goal.target_return_pct) if goal else Decimal(0)
    ret_pct = (
        (total_value_krw - total_cost_krw) / total_cost_krw * 100
        if total_cost_krw
        else Decimal(0)
    )
    return {
        "return_pct": ret_pct,
        "gap_pct": ret_pct - target,  # 음수 = 목표 미달
        "cost_krw": total_cost_krw,
        "value_krw": total_value_krw,
        "by_currency": {
            c: {"cost_krw": v[0], "value_krw": v[1]} for c, v in by_cur.items()
        },
        "cost_labels": labels,  # {exact: n, approx_first_buy: m, ...} 정직성 표시
    }


def compute_allocation_gap(user) -> dict:
    """배치 갭 = KRW 통합 유휴현금 비중(현금 / (현금+보유평가)). 구조·사실.

    numéraire=KRW: USD 현금·보유를 현재 환율로 KRW 평가 후 통합.
    반환: {"cash_krw","holdings_value_krw","idle_ratio","by_currency"}.
    """
    cash_krw, hold_krw = Decimal(0), Decimal(0)
    by_cur: dict[str, list] = {}

    for cb in CashBalance.objects.filter(wallet__user=user):
        rate = _krw_rate(cb.currency)
        v = cb.amount * rate
        cash_krw += v
        by_cur.setdefault(cb.currency, [Decimal(0), Decimal(0)])[0] += v

    holdings = WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    for h in holdings:
        rate = _krw_rate(h.stock.currency)
        v = h.shares * _current_price(h.stock) * rate
        hold_krw += v
        by_cur.setdefault(h.stock.currency, [Decimal(0), Decimal(0)])[1] += v

    total = cash_krw + hold_krw
    idle_ratio = (cash_krw / total) if total else Decimal(1)
    return {
        "cash_krw": cash_krw,
        "holdings_value_krw": hold_krw,
        "idle_ratio": idle_ratio,
        "by_currency": {
            c: {"cash_krw": v[0], "holdings_value_krw": v[1]}
            for c, v in by_cur.items()
        },
    }


def determine_mode(progress_gap: dict, allocation_gap: dict) -> str:
    """모드 분기(KRW 통합 정본): (유휴현금 임계 초과 OR 목표 미달) → BUY, else DEFEND.

    - BUY  = 매수 여력(KRW 현금) 또는 목표 미달(KRW 갭<0)
    - DEFEND = 완전투자 & 목표 달성
    """
    idle_high = allocation_gap["idle_ratio"] > IDLE_CASH_THRESHOLD
    below_target = progress_gap["gap_pct"] < 0
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

    # 가드레일 1 + 통화 분리: 해당 통화 현금 여력(환전 없음). KRW 환산 소계로 판정.
    cur_alloc = allocation_gap.get("by_currency", {}).get(currency)
    if not cur_alloc:
        return []
    cur_cash = cur_alloc["cash_krw"]
    cur_total = cur_cash + cur_alloc["holdings_value_krw"]
    cur_idle = (cur_cash / cur_total) if cur_total else Decimal(0)
    if cur_idle < IDLE_CASH_THRESHOLD:
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


def fx_context(pair: str = "USDKRW") -> dict:
    """현재 환율의 역사적 백분위(백필 시계열 대비). **사실·맥락 — 예측 아님.**

    distance_from_entry와 동성격. 랭킹·모드 판정에 가중치로 넣지 않는다(그건 19c).
    반환: {available, pair, spot, percentile, sample_n, span, note} 또는 {available:False}.
    """
    from django.db.models import Max, Min

    from packages.shared.fx.models import ExchangeRate
    from packages.shared.fx.services import get_spot_rate

    spot = get_spot_rate(pair)
    if spot is None:
        return {"available": False}

    rates = list(
        ExchangeRate.objects.filter(pair=pair).values_list("close", flat=True)
    )
    if not rates:
        return {"available": False}

    below = sum(1 for r in rates if r <= spot)
    percentile = round(below / len(rates) * 100, 1)
    dates = ExchangeRate.objects.filter(pair=pair).aggregate(
        lo=Min("date"), hi=Max("date")
    )
    return {
        "available": True,
        "pair": pair,
        "spot": spot,
        "percentile": percentile,
        "sample_n": len(rates),
        "span": {"from": dates["lo"], "to": dates["hi"]},
        "note": (
            f"현재 {pair} {spot}는 {dates['lo']}~{dates['hi']} 대비 "
            f"{percentile:.0f}백분위 (사실·맥락, 예측 아님)"
        ),
    }


def _cost_basis_note(labels: dict) -> str:
    """KRW 취득원가 근사 포함 여부를 사실로 명시(정직성 장치, '예측 아님'과 동렬)."""
    approx = labels.get("approx_first_buy", 0) + labels.get("approx_low_confidence", 0)
    if approx:
        return f"KRW 원가 {approx}건은 매수일/근사 환율 기준(정본 아님, 사용자 정정 시 exact)."
    return "KRW 원가 전건 정확(exact/native_krw)."


def recommend(user) -> dict:
    """목표-대비 권유 산출(계약 v2, KRW 기준). action ∈ {BUY, HOLD, TRIM}.

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
        for currency in allocation["by_currency"]:
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
            "numeraire": "KRW",
            "cost_basis_note": _cost_basis_note(progress["cost_labels"]),
            "fx_context": fx_context("USDKRW"),  # 역사적 백분위(사실·맥락, 예측 아님)
        },
        "recommendations": recommendations,
        "disclaimer": DISCLAIMER,
    }
