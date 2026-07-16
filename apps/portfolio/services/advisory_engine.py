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


# ============================================================
# 드로다운 비례 다이얼 (SLICE19C — 하드 10% 버퍼 게이트 대체)
# ============================================================

BASELINE_BUFFER = Decimal("0.10")  # 기존 하드 10% = 다이얼 baseline(무드로다운·무손잡이 재현)
FLOOR_BUFFER = Decimal("0.03")  # 불가침 바닥 3% = 엔진 고정 가치관 "현금 3%는 남긴다"


def _knobs(goal) -> dict:
    """UserGoal 손잡이 5종 (없으면 전부 보수 기본값). 엔진은 이 값을 자동 조정하지 않는다."""
    if goal is None:
        return {"A": 0, "G": 0, "w": Decimal("0"), "L": 30, "E": 0}
    return {
        "A": goal.aggressiveness_offset,
        "G": goal.growth_boost,
        "w": goal.diversification_weight,
        "L": goal.concentration_limit,
        "E": goal.exploration_ratio,
    }


def compute_dial(user, allocation: dict, goal=None) -> dict:
    """드로다운 비례 다이얼 → 통화별 매수 여력(deployable). 하드 10% 게이트 대체.

        a    = dd + A%p + G%p·𝟙(신고점 국면)          # 자동 반응은 dd(측정 사실)뿐
        버퍼 = max(10% − a, 3%)                        # 바닥 3% 불가침
        여력 = 유휴현금 비중 − 버퍼                     # 통화별 현금 비례 배분, 음수 0 클램프

    dd/is_new_high는 flow 조정 드로다운(snapshot.compute_drawdown). 스냅샷 없으면 dd=0·
    신고점(=기본 버퍼 10% = 기존 게이트 재현). A·G는 %p(정수) → /100 환산.
    """
    from apps.portfolio.services.snapshot import compute_drawdown

    if goal is None:
        from apps.portfolio.services.my_container import get_goal_for_user

        goal = get_goal_for_user(user)
    k = _knobs(goal)
    dd_info = compute_drawdown(user)
    dd = dd_info["dd"]
    is_new_high = dd_info["is_new_high"]

    a = dd + Decimal(k["A"]) / 100
    if is_new_high:
        a += Decimal(k["G"]) / 100  # G는 신고점 국면에서만
    buffer = max(BASELINE_BUFFER - a, FLOOR_BUFFER)

    total = allocation["cash_krw"] + allocation["holdings_value_krw"]
    cash_total = allocation["cash_krw"]
    idle_ratio = allocation["idle_ratio"]
    headroom_frac = max(Decimal(0), idle_ratio - buffer)
    buffer_krw = buffer * total  # 예약할 총 버퍼 KRW

    by_cur = {}
    for cur, v in allocation["by_currency"].items():
        cash = v["cash_krw"]
        # 버퍼의 통화별 현금 비례 배분(현금 많은 통화가 버퍼 더 부담)
        share = (buffer_krw * (cash / cash_total)) if cash_total > 0 else Decimal(0)
        deployable = max(Decimal(0), cash - share)
        by_cur[cur] = {
            "cash_krw": cash,
            "buffer_share_krw": share,
            "deployable_krw": deployable,
            "headroom_ratio": (deployable / cash) if cash > 0 else Decimal(0),
        }

    return {
        "dd": dd,
        "a": a,
        "buffer": buffer,
        "is_new_high": is_new_high,
        "idle_ratio": idle_ratio,
        "headroom_frac": headroom_frac,
        "buffer_krw": buffer_krw,
        "deployable_krw_total": headroom_frac * total,
        "by_currency": by_cur,
        "knobs": k,
        "frozen": dd_info.get("frozen", False),
        "window_days": dd_info.get("window_days", 0),
        "dd_available": dd_info.get("available", False),
    }


def determine_mode(progress_gap: dict, dial: dict) -> str:
    """모드 분기(KRW 통합 정본): (매수 여력 있음 OR 목표 미달) → BUY, else DEFEND.

    SLICE19C: 하드 10% 대신 **다이얼 deployable**(버퍼 차감 후 배치 가능 현금)으로 판정.
    - BUY  = 다이얼 여력(deployable_krw_total > 0) 또는 목표 미달(KRW 갭<0)
    - DEFEND = 여력 0 & 목표 달성
    """
    has_headroom = dial["deployable_krw_total"] > 0
    below_target = progress_gap["gap_pct"] < 0
    return "BUY" if (has_headroom or below_target) else "DEFEND"


# ============================================================
# 코어 랭킹 (SLICE19C 하이브리드 B′) + 탐험 레인 + L 게이트
# ============================================================

# 배치 우선순위 점수 성분 가중(기대수익 아님). w 상한 0.20에도 신뢰도(0.48)가 최대 성분.
CONF_WEIGHT = Decimal("0.60")
ENTRY_WEIGHT = Decimal("0.25")
CCY_WEIGHT = Decimal("0.15")
ENTRY_SPAN = Decimal("20")  # 진입가 여유 정규화 스팬(±%p → [0,1])
YOUNG_DAYS = 30  # 탐험 레인 젊음 기준(STEP 0 (c) 실측 자리표시 — evidence_count는 무판별)


def _clamp01(x: Decimal) -> Decimal:
    return Decimal(0) if x < 0 else (Decimal(1) if x > 1 else x)


def _relation_edge(candidate_symbol, holding_symbols):
    """후보-보유 연결 중 최강(truth_score max) 엣지의 (truth_score, first_observed_at).

    연결 없으면 (0.0, None). 젊음 판정과 신뢰도 점수를 같은 엣지에서 뽑는다.
    """
    if not holding_symbols:
        return (0.0, None)
    from django.db.models import Q

    from apps.chain_sight.models.relation_discovery import RelationConfidence

    rows = list(
        RelationConfidence.objects.filter(
            Q(symbol_a=candidate_symbol, symbol_b__in=holding_symbols)
            | Q(symbol_b=candidate_symbol, symbol_a__in=holding_symbols)
        ).values_list("truth_score", "first_observed_at")
    )
    if not rows:
        return (0.0, None)
    return max(rows, key=lambda r: r[0])


def _relation_score(candidate_symbol, holding_symbols) -> float:
    """후보-보유 최강 엣지 truth_score(해자). 연결 없으면 0.0."""
    return _relation_edge(candidate_symbol, holding_symbols)[0]


def _is_young(first_observed_at) -> bool:
    """최강 연결 엣지의 관측 시작이 YOUNG_DAYS 미만 = 젊은(관측 이력 짧은) 후보.

    ★ 신뢰도를 보정하지 않는다(젊음 가산점 금지) — 배정만 분리(탐험 레인).
    """
    if first_observed_at is None:
        return False
    from django.utils import timezone

    return (timezone.now() - first_observed_at).days < YOUNG_DAYS


def _entry_score(distance_from_entry) -> Decimal:
    """진입가 여유 → [0,1]. 목표가 아래(distance<0)일수록 높음. None=0.5(중립)."""
    if distance_from_entry is None:
        return Decimal("0.5")
    d = Decimal(str(distance_from_entry))
    return _clamp01(Decimal("0.5") - d / (2 * ENTRY_SPAN))


def _placement_score(conf, entry, ccy, div, w) -> Decimal:
    """배치 우선순위 점수(기대수익 아님).

        (1−w)×(0.60·신뢰도 + 0.25·진입가 + 0.15·통화여력) + w×분산 한계효과
    w=0(기본)이면 분산 영향 정확히 0. 신뢰도 지배 불변식(w≤0.20 → 신뢰도 0.48 최대).
    """
    base = CONF_WEIGHT * conf + ENTRY_WEIGHT * entry + CCY_WEIGHT * ccy
    return (Decimal(1) - w) * base + w * div


def _currency_positions_krw(user, currency):
    """통화 버킷의 (심볼→KRW 평가) dict + 버킷 총액(보유+현금) KRW. div/자격 게이트용."""
    rate = _krw_rate(currency)
    holdings = WalletHolding.objects.filter(
        wallet__user=user, stock__currency=currency
    ).select_related("stock")
    pos: dict[str, Decimal] = {}
    hold_krw = Decimal(0)
    for h in holdings:
        v = h.shares * _current_price(h.stock) * rate
        pos[h.stock.symbol] = pos.get(h.stock.symbol, Decimal(0)) + v
        hold_krw += v
    cash_krw = sum(
        (cb.amount * rate for cb in CashBalance.objects.filter(wallet__user=user, currency=currency)),
        Decimal(0),
    )
    return pos, hold_krw + cash_krw


def _buy_analysis(pos, bucket_total, symbol, deployable_krw, L_frac):
    """매수 자격 + 분산 한계효과 (L 준수 트랜치).

    room = L 한도까지 남은 여유(= L×총액 − 기존). **자격 = room>0**(기존 집중도<L →
    매수 여지 있음). 표준 트랜치 = min(매수여력, room) — L을 넘지 않게 캡(매수는 L까지만).
    분산 한계효과 = 0.5 + (before_max − after_max) 클램프(개선>0.5, 악화<0.5).
    반환: {eligible, div, tranche, after_conc}.
    """
    if bucket_total <= 0:
        return {"eligible": False, "div": Decimal("0.5"), "tranche": Decimal(0), "after_conc": Decimal(0)}
    existing = pos.get(symbol, Decimal(0))
    room = L_frac * bucket_total - existing
    if room <= 0:  # 기존 집중도 >= L → 매수 자격 없음(더 담지 않음)
        return {"eligible": False, "div": Decimal("0.5"), "tranche": Decimal(0), "after_conc": existing / bucket_total}
    tranche = min(deployable_krw, room)
    cand_after = (existing + tranche) / bucket_total
    before_max = max((v / bucket_total for v in pos.values()), default=Decimal(0))
    after_max = max(before_max, cand_after)
    div = _clamp01(Decimal("0.5") + (before_max - after_max))
    return {"eligible": True, "div": div, "tranche": tranche, "after_conc": cand_after}


def rank_candidates(user, currency, dial, goal=None) -> list:
    """매수 후보 랭킹(하이브리드 B′) + 탐험 레인 분리. 통화 분리(환전 없음).

    게이트: ⑴ 통화 여력 0(dial deployable≤0) → 자격 박탈([]). ⑵ 매수 시 집중도>L → 제외.
    코어: 배치 우선순위 점수 내림. 탐험(E>0): 젊은 후보 전용, 서열=진입가·통화여력(신뢰도 없음).
    반환: 평탄 리스트(core 먼저, 각 항목 lane 태그).
    """
    from packages.shared.users.models import WatchlistItem

    cur_dial = dial.get("by_currency", {}).get(currency)
    if not cur_dial or cur_dial["deployable_krw"] <= 0:  # 통화 여력 0 자격 박탈
        return []
    tranche = cur_dial["deployable_krw"]  # 표준 트랜치 = 통화 매수여력
    headroom_ratio = cur_dial["headroom_ratio"]

    k = _knobs(goal if goal is not None else None)
    if goal is None:
        from apps.portfolio.services.my_container import get_goal_for_user

        k = _knobs(get_goal_for_user(user))
    L_frac = Decimal(k["L"]) / 100
    w = k["w"]
    E = k["E"]

    holding_symbols = [
        h.stock.symbol
        for h in WalletHolding.objects.filter(
            wallet__user=user, stock__currency=currency
        ).select_related("stock")
    ]
    pos, bucket_total = _currency_positions_krw(user, currency)

    core, explore = [], []
    for wi in WatchlistItem.objects.filter(watchlist__user=user).select_related("stock"):
        if wi.stock.currency != currency:  # 통화 분리
            continue
        conf, first_obs = _relation_edge(wi.stock.symbol, holding_symbols)
        ba = _buy_analysis(pos, bucket_total, wi.stock.symbol, tranche, L_frac)
        if not ba["eligible"]:  # 매수 자격 없음(기존 집중도 >= L)
            continue
        div = ba["div"]
        entry = _entry_score(wi.distance_from_entry)
        young = _is_young(first_obs)
        item = {
            "symbol": wi.stock.symbol,
            "currency": currency,
            "relation_score": conf,
            "distance_from_entry": wi.distance_from_entry,
            "headroom_ratio": headroom_ratio,
            "div_score": div,
            "is_young": young,
        }
        if E > 0 and young:  # 탐험 레인: 젊은 후보 전용
            item["lane"] = "exploration"
            item["score"] = _placement_score(
                Decimal(0), entry, headroom_ratio, div, Decimal(0)
            )  # 신뢰도 성분 없음(낮음이 전제)
            explore.append(item)
        else:
            item["lane"] = "core"
            item["score"] = _placement_score(
                Decimal(str(conf)), entry, headroom_ratio, div, w
            )
            core.append(item)

    core.sort(key=lambda x: -x["score"])
    # 탐험 서열 = 진입가 여유·통화 여력(신뢰도 없음)
    explore.sort(key=lambda x: -(_entry_score(x["distance_from_entry"]) + x["headroom_ratio"]))
    return core + explore


def find_trim_candidates(user, goal=None) -> list:
    """가드레일 2: 통화별 집중도 > L → TRIM 후보 (SLICE19C: 하드 30% → L 손잡이).

    비중 = 종목 평가액 / (해당 통화 총 배치). L=100(무제한)이면 TRIM 소멸.
    (부가) 기여도 = 고점 대비 이 보유의 감소 기여(사실 문구) — 실패 시 스킵.
    """
    k = _knobs(goal if goal is not None else None)
    if goal is None:
        from apps.portfolio.services.my_container import get_goal_for_user

        k = _knobs(get_goal_for_user(user))
    L_frac = Decimal(k["L"]) / 100

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
        if weight > L_frac:  # L=100 → weight>1.0 불가 → TRIM 소멸
            trims.append({"symbol": h.stock.symbol, "currency": cur, "weight": weight})
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


def _max_concentration(user) -> dict | None:
    """최대 보유 집중도(사실 — L 값 무관 항상 표기, §0-7). 통화 버킷별 비중 최대."""
    holdings = list(
        WalletHolding.objects.filter(wallet__user=user).select_related("stock")
    )
    if not holdings:
        return None
    valued = [(h, h.shares * _current_price(h.stock)) for h in holdings]
    total_by_cur: dict[str, Decimal] = {}
    for h, v in valued:
        total_by_cur[h.stock.currency] = total_by_cur.get(h.stock.currency, Decimal(0)) + v
    for cb in CashBalance.objects.filter(wallet__user=user):
        total_by_cur[cb.currency] = total_by_cur.get(cb.currency, Decimal(0)) + cb.amount
    best = None
    for h, v in valued:
        total = total_by_cur[h.stock.currency]
        weight = (v / total) if total else Decimal(0)
        if best is None or weight > best["weight"]:
            best = {"symbol": h.stock.symbol, "currency": h.stock.currency, "weight": weight}
    return best


def _advisory_notes(dial: dict, k: dict) -> list:
    """자동 장치 작동 + 손잡이 적용을 사실 문구로(§0-7 사실 보고 원칙)."""
    notes = []
    if dial.get("frozen"):
        notes.append("가격 신선도 밖(영업일 2일 초과) — dd 직전 유효값 동결")
    if dial["dd"] > 0:
        notes.append(f"드로다운 {dial['dd'] * 100:.1f}% 반영(입출금 flow 제외·환율 자동)")
    if dial["buffer"] == FLOOR_BUFFER:
        notes.append("버퍼 바닥 3% 클램프(불가침 불변식)")
    if k["A"]:
        notes.append(f"사용자 공격성 +{k['A']}%p")
    if k["G"] and dial["is_new_high"]:
        notes.append(f"성장 부스트 +{k['G']}%p(신고점 국면)")
    if k["w"]:
        notes.append(f"분산 가중 w={k['w']}")
    if k["L"] != 30:
        notes.append(f"집중도 한도 L={k['L']}%")
    if k["E"]:
        notes.append(f"탐험 배정 E={k['E']}%")
    return notes


def _jsonable(obj):
    """AdvisoryRun.output/knobs JSON 저장용 재귀 직렬화(Decimal→str, date→iso)."""
    import datetime as _dt

    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def run_advisory(user, trigger: str = "manual"):
    """엔진 실행 진입점: 스냅샷 upsert(이중 기록) + recommend + AdvisoryRun 기록.

    recommend()는 순수 계산(부작용 없음) — 이 함수가 영속화를 담당(테스트 격리).
    trigger(SLICE20A): "auto"=nightly 자동, "manual"=화면 수동 진단(기본).
    반환: recommend() 산출(계약 v3).
    """
    from apps.portfolio.models_my import AdvisoryRun
    from apps.portfolio.services.snapshot import upsert_snapshot

    snap = upsert_snapshot(user)
    result = recommend(user)
    dial = result["summary"]["dial"]
    knobs_snap = {
        **result["summary"]["knobs"],
        "dd": dial["dd"],
        "buffer": dial["buffer"],
        "deployable_krw_total": dial["deployable_krw_total"],
    }
    AdvisoryRun.objects.create(
        user=user,
        snapshot=snap,
        trigger=trigger,
        output=_jsonable(result),
        knobs_snapshot=_jsonable(knobs_snap),
    )
    return result


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
    k = _knobs(goal)
    progress = compute_progress_gap(user, goal)
    allocation = compute_allocation_gap(user)
    dial = compute_dial(user, allocation, goal)
    mode = determine_mode(progress, dial)

    recommendations = []

    # 가드레일 2: TRIM (집중도 > L, 모드 무관 항상 검사)
    trim_symbols = set()
    for t in find_trim_candidates(user, goal):
        trim_symbols.add(t["symbol"])
        recommendations.append(
            {
                "action": "TRIM",
                "symbol": t["symbol"],
                "currency": t["currency"],
                "score": None,
                "lane": "core",
                "rationale": (
                    f"통화별 집중도 {t['weight'] * 100:.0f}% > 한도 {k['L']}% "
                    "— 배치 규칙(예측 아님)"
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
                    "lane": "core",
                    "rationale": "집중도 정상 — 보유 유지",
                }
            )

    # BUY: 매수 모드 & 통화별 여력 있는 후보 (하이브리드 배치 우선순위 점수 + 탐험 레인)
    if mode == "BUY":
        for currency in dial["by_currency"]:
            for c in rank_candidates(user, currency, dial, goal):
                dist = c["distance_from_entry"]
                dist_txt = f"진입가 여유 {dist:.1f}%" if dist is not None else "진입가 미설정"
                if c["lane"] == "exploration":
                    rationale = (
                        f"탐험 레인: {dist_txt}, 통화 여력 {c['headroom_ratio'] * 100:.0f}% "
                        "— 신뢰도 축적 중·사용자 탐험 배정(예측 아님)"
                    )
                else:
                    rationale = (
                        f"관계 신뢰도 {c['relation_score']:.2f}, {dist_txt} "
                        "— 배치 우선순위 점수(기대수익 아님)"
                    )
                recommendations.append(
                    {
                        "action": "BUY",
                        "symbol": c["symbol"],
                        "currency": currency,
                        "score": c["score"],
                        "lane": c["lane"],
                        "rationale": rationale,
                    }
                )

    return {
        "mode": mode,
        "summary": {
            "progress_gap": progress,
            "allocation_gap": allocation,
            "goal_target_return_pct": (goal.target_return_pct if goal else None),
            "numeraire": "KRW",
            "cost_basis_note": _cost_basis_note(progress["cost_labels"]),
            "fx_context": fx_context("USDKRW"),  # 역사적 백분위(사실·맥락, 예측 아님)
            # --- 계약 v3 (SLICE19C) ---
            "dial": {
                "dd": dial["dd"],
                "a": dial["a"],
                "buffer": dial["buffer"],
                "is_new_high": dial["is_new_high"],
                "headroom_frac": dial["headroom_frac"],
                "deployable_krw_total": dial["deployable_krw_total"],
                "frozen": dial["frozen"],
                "window_days": dial["window_days"],
                "by_currency": dial["by_currency"],
            },
            "knobs": k,  # 손잡이 5종 스냅(사후분석·사실 보고)
            "max_concentration": _max_concentration(user),  # 사실 항상 표기(L 무관)
            "notes": _advisory_notes(dial, k),  # 자동 장치 + 손잡이 적용 사실
        },
        "recommendations": recommendations,
        "disclaimer": DISCLAIMER,
    }
