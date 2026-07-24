"""
Card Detail endpoints (PR-J).

소속: apps/market_pulse/api/views (app 레이어 DRF Views).
역할: 4 카드 디테일 엔드포인트(Regime/Breadth/Sector/Concentration) — 시계열 또는
  세부 메트릭 응답. cache.py 키 빌더로 Redis 캐시.
소비처: 마켓 펄스 화면 카드 드릴다운.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.utils import timezone as django_timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_pulse.api import cache as cache_keys
from apps.market_pulse.management.commands.backfill_v2_regime_vectors import (
    BACKFILL_MARK,  # 소급 합성행 provenance 마커 단일 소스(드리프트 방지)
)
from apps.market_pulse.constants import (
    CD_MOMENTUM_BASELINE,
    CD_REL_STRENGTH_5D_LOOKBACK,
    CD_REL_STRENGTH_BASELINE,
    classify_cd_state,
    derive_rel_strength_5d,
    resolve_official_cd_state,
)
from apps.market_pulse.models.analog_context import AnalogDayContext
from apps.market_pulse.models.briefing import BriefingLog
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)
from apps.market_pulse.regime.classifier import load_rules
from apps.market_pulse.regime.component_cuts import build_components
from apps.market_pulse.regime.next_stage import compute_next_stage_margin
from apps.market_pulse.throttles import (
    MarketPulseHourThrottle,
    MarketPulseLLMThrottle,
    MarketPulseUserThrottle,
)
from macro.models.indicators import MarketIndex, MarketIndexPrice

VALID_CARDS = {"regime", "breadth", "sector", "concentration", "brief"}

# CD-STAB Slice A′ (D-CD-XAXIS-SCOPE): 판단 x축 = 5일 상대수익의 벤치마크.
#   sector momentum_5d(저장값)에서 이 벤치 5일 수익률을 빼 rel_strength_5d 파생(서빙 시점).
CD_BENCH_SYMBOL = "SPY"


def _bench_5d_return_by_date() -> dict:
    """벤치(SPY) 5거래일 수익률(%)을 거래일별로 파생 — 서빙 시점 계산(저장 0, 규칙 #3).

    `SectorFlowSnapshot.momentum_5d`(섹터 5일 수익률)와 동일 창(5거래일 룩백) 정합.
    sector momentum 계산기(calculators/sector_flow._momentum)와 동형: close[i] 대비 5행 전.
    초기 5거래일(소급 부족)·close 결측 날은 dict 미기입 → 소비 측 None(정직한 null, 규칙 #5).
    """
    idx = MarketIndex.objects.filter(symbol=CD_BENCH_SYMBOL).first()
    if idx is None:
        return {}
    rows = list(
        MarketIndexPrice.objects.filter(index=idx)
        .order_by("date")
        .values_list("date", "close")
    )
    out: dict = {}
    n = CD_REL_STRENGTH_5D_LOOKBACK
    for i in range(n, len(rows)):
        d, close = rows[i]
        start = rows[i - n][1]
        if close is None or start is None or start == 0:
            continue  # 소급 불가 → 미기입(발명·보간 금지)
        out[d] = (Decimal(close) - Decimal(start)) / Decimal(start) * Decimal("100")
    return out


def _envelope(payload: dict, started: float, *, cache_state: str) -> dict:
    return {
        "_meta": {
            "generated_at": django_timezone.now().isoformat(),
            "latency_ms": int((time.time() - started) * 1000),
            "cache": cache_state,
        },
        "data": payload,
    }


# MP2-TREND S2: 조회-시 파생 helper(모델 저장 0). breadth 기준선(A/D선 MA20)·이탈 streak 산출.
#   D-TREND-BASELINE(옵션 C 2호 몫): 기준선 = A/D선의 20일 이동평균(파생). 임계 밴드는 3호.
def _sma_series(values: list[int], window: int) -> list[float | None]:
    """단순이동평균 시계열. 앞선 데이터가 window 미만인 구간은 None(경계 명시 처리)."""
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(round(sum(values[i - window + 1 : i + 1]) / window, 2))
    return out


def _deviation_streak(ad_lines: list[int], ma_series: list[float | None]) -> int:
    """최신일부터 역방향으로 A/D선이 기준선(MA) 아래(<)인 연속 일수. MA None이면 중단."""
    streak = 0
    for i in range(len(ad_lines) - 1, -1, -1):
        ma = ma_series[i]
        if ma is None or ad_lines[i] >= ma:
            break
        streak += 1
    return streak


@extend_schema(
    summary="Card detail (lazy load)",
    description="Layer 1 lazy load. brief는 30분 캐시, 그 외는 5분.",
    tags=["Market Pulse v2"],
    parameters=[
        OpenApiParameter(
            name="card_id",
            type=str,
            location=OpenApiParameter.PATH,
            enum=["regime", "breadth", "sector", "concentration", "brief"],
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)
class CardDetailView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def get_throttles(self):
        card_id = (self.kwargs.get("card_id") or "").lower()
        throttles = [c() for c in self.throttle_classes]
        if card_id == "brief":
            throttles.append(MarketPulseLLMThrottle())
        return throttles

    def get(self, request, card_id: str, *args, **kwargs):
        started = time.time()
        card_id = (card_id or "").lower()
        if card_id not in VALID_CARDS:
            return Response({"error": f"unknown card: {card_id}"}, status=404)

        key = cache_keys.card_detail_key(card_id, brief=(card_id == "brief"))
        cached = cache.get(key)
        if cached is not None:
            return Response(_envelope(cached, started, cache_state="HIT"))

        payload = {
            "regime": _regime_detail,
            "breadth": _breadth_detail,
            "sector": _sector_detail,
            "concentration": _concentration_detail,
            "brief": _brief_detail,
        }[card_id]()

        ttl = cache_keys.card_detail_ttl(card_id)
        cache.set(key, payload, timeout=ttl)
        return Response(_envelope(payload, started, cache_state="MISS"))


@extend_schema(
    summary="Regime z-anomaly (S4)",
    description=(
        "국면 성분 z-이상도 시계열. baseline = 소급 모집단(고정 잣대) μ·σ(표본). "
        "z는 serve-time·미저장. 24h 캐시. 다운샘플(최근 90영업일 일간 + 이전 주간)."
    ),
    tags=["Market Pulse v2"],
    responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
)
class RegimeZScoreView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def get(self, request, *args, **kwargs):
        from django.db.models import Max, Min

        started = time.time()
        bound = RegimeSnapshot.objects.filter(summary=BACKFILL_MARK).aggregate(
            mn=Min("date"), mx=Max("date")
        )
        if bound["mn"] is None:
            # 소급 모집단 부재 → 빈 응답(발명 금지).
            empty = {"available": False, "components": [], "meta": {}}
            return Response(_envelope(empty, started, cache_state="MISS"))

        key = cache_keys.regime_zscore_key(bound["mn"], bound["mx"])
        try:
            cached = cache.get(key)
        except Exception:  # pragma: no cover - 캐시 장애 폴백
            cached = None
        if cached is not None:
            return Response(_envelope(cached, started, cache_state="HIT"))

        payload = _regime_zscore_detail()
        try:
            cache.set(key, payload, timeout=cache_keys.REGIME_ZSCORE_TTL_SEC)
        except Exception:  # pragma: no cover - 캐시 장애 폴백(재계산으로 응답)
            pass
        return Response(_envelope(payload, started, cache_state="MISS"))


@extend_schema(
    summary="Regime analog card (Slice B)",
    description=(
        "유사 국면 카드 결정론 코어. 오늘 z-벡터 가족가중 최근접(②C) + 이웃 SPY 선도수익 "
        "지평별 정직 팬(①C). 뉴스·LLM 무의존. label 슬롯 null(Slice C). 1h 캐시."
    ),
    tags=["Market Pulse v2"],
    responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
)
class RegimeAnalogView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def get(self, request, *args, **kwargs):
        from django.db.models import Max

        started = time.time()
        today = django_timezone.localdate()
        wend = RegimeSnapshot.objects.filter(summary=BACKFILL_MARK).aggregate(
            mx=Max("date")
        )["mx"]
        if wend is None:
            return Response(
                _envelope({"available": False}, started, cache_state="MISS")
            )
        key = cache_keys.regime_analog_key(today, wend)
        try:
            cached = cache.get(key)
        except Exception:  # pragma: no cover - 캐시 장애 폴백
            cached = None
        if cached is not None:
            return Response(_envelope(cached, started, cache_state="HIT"))

        payload = _regime_analog_detail()
        try:
            cache.set(key, payload, timeout=cache_keys.REGIME_ANALOG_TTL_SEC)
        except Exception:  # pragma: no cover - 캐시 장애 폴백
            pass
        return Response(_envelope(payload, started, cache_state="MISS"))


def _regime_detail():
    today = django_timezone.localdate()
    snap = RegimeSnapshot.objects.filter(date=today).first()
    if snap is None:
        snap = RegimeSnapshot.objects.order_by("-date").first()
    if snap is None:
        return {"available": False}
    # MP-UX-S3a: 국면 타임라인 데이터원 (breadth/concentration history_30d 패턴 재사용).
    # stage = raw regime enum 배열 — 라벨 변환(regime.*)은 FE 담당. 빈데이터 graceful(빈 배열).
    history = list(
        RegimeSnapshot.objects.order_by("-date")[:30].values(
            "date", "regime", "previous_regime", "inputs"
        )
    )
    history.reverse()
    # MP2-TREND S2(additive): 전환일 파생 — previous_regime≠regime인 날짜(조회-시, 저장 0).
    #   양 STEP 0 교차 확정 규칙: transitioned 미저장 → BE 조회-시 파생, FE 파생 금지.
    #   빈 previous_regime(초기 스냅샷)은 전환 아님. 날짜당 1행이라 자연 dedup.
    transition_dates = [
        h["date"].isoformat()
        for h in history
        if h["previous_regime"] and h["previous_regime"] != h["regime"]
    ]
    # MP-UX-S3b: 다음(인접 상위) 단계까지 거리. rules.yaml 읽기만(임계 단일소스), 모델 저장 0(즉석 산출).
    ns = compute_next_stage_margin(snap.regime, snap.inputs)
    # MP2-TREND S3(R1): 국면 재료 판정-거리 — 룰-구동 7지표 raw 시계열 + 컷(rules.yaml 도출) + 판정거리.
    #   z-score 아님(STEP 0 반증, D-TREND-BASELINE-R1). 컷 하드코딩 0(rules.yaml 단일소스). 저장 0.
    components = build_components(history, load_rules())
    return {
        "available": True,
        "date": snap.date.isoformat(),
        "regime": snap.regime,
        "previous_regime": snap.previous_regime,
        "status": snap.status,
        "coverage": float(snap.coverage),
        "inputs": snap.inputs,
        "fired_rules": snap.fired_rules or [],
        "hysteresis_streak": snap.hysteresis_streak,
        "headline": snap.headline,
        "is_finalized": snap.is_finalized,
        "regime_history_30d": [
            {"date": h["date"].isoformat(), "stage": h["regime"]} for h in history
        ],
        "transition_dates": transition_dates,
        "next_stage": ns["next_stage"],
        "margins": ns["margins"],
        "next_stage_closest": ns["closest"],
        "components": components,
    }


# MP2-TREND S4 (D-S4-*): 국면 성분 z-이상도 — 전용 빌더(기존 _regime_detail 무변경).
#   baseline = 고정 소급 모집단(summary=BACKFILL_MARK)의 μ·σ(표본), z는 serve-time·미저장.
#   대상 = raw 탭 대칭 7 룰-구동 지표(TARGET_INDICATORS). baseline 함수는 전 14성분 산출
#   (ANALOG 재사용 대비). 다운샘플: 최근 90영업일 일간 + 그 이전 주간.
def _regime_zscore_detail() -> dict:
    from apps.market_pulse.regime.component_cuts import (
        INDICATOR_UNITS,
        TARGET_INDICATORS,
    )
    from apps.market_pulse.regime.inputs import ALL_INPUT_KEYS
    from apps.market_pulse.regime.zscore import (
        compute_baseline,
        downsample,
        z_of,
    )

    # 소급 모집단(고정 잣대) — 날짜 오름차순 inputs.
    syn = list(
        RegimeSnapshot.objects.filter(summary=BACKFILL_MARK)
        .order_by("date")
        .values_list("date", "inputs")
    )
    if not syn:
        return {"available": False, "components": [], "meta": {}}
    pop = [inp for _, inp in syn]
    baseline = compute_baseline(pop, ALL_INPUT_KEYS)

    # 전체 행(소급 + 라이브) — summary 미선택 → 마커 미노출. 다운샘플 적용.
    all_rows = list(
        RegimeSnapshot.objects.order_by("date").values_list("date", "inputs")
    )
    ds_rows = downsample(all_rows)

    components = []
    for key in TARGET_INDICATORS:
        base = baseline.get(key) or {"mean": None, "std": None, "n": 0, "insufficient": True}
        series = [
            {"date": d.isoformat(), "z": z_of((inp or {}).get(key), base)}
            for d, inp in ds_rows
        ]
        components.append(
            {
                "key": key,
                "unit": INDICATOR_UNITS.get(key, ""),
                "series": series,
                "baseline": {
                    "mean": round(base["mean"], 4) if base["mean"] is not None else None,
                    "std": round(base["std"], 4) if base["std"] is not None else None,
                    "n": base["n"],
                },
                "insufficient": bool(base["insufficient"]),
            }
        )

    # low_confidence_until = 소급창 시작 후 20영업일째(초입 저신뢰 음영 경계).
    syn_dates = [d for d, _ in syn]
    low_conf = syn_dates[19] if len(syn_dates) >= 20 else syn_dates[-1]
    live_start = (
        RegimeSnapshot.objects.exclude(summary=BACKFILL_MARK)
        .order_by("date")
        .values_list("date", flat=True)
        .first()
    )
    return {
        "available": True,
        "components": components,
        "meta": {
            "low_confidence_until": low_conf.isoformat(),
            "live_start": live_start.isoformat() if live_start else None,
            "downsample_recent_daily": 90,
        },
    }


# MP2-ANALOG Slice B: 유사 국면 카드 결정론 코어(뉴스·LLM 무의존).
#   오늘 z-벡터 vs 소급 모집단 가족가중 최근접(②C) + 이웃 SPY 선도수익 지평별 정직 팬(①C).
#   label 슬롯(cat_slot·why)은 null — Slice C가 채움.
def _regime_analog_detail() -> dict:
    from django.utils import timezone as _tz

    from apps.market_pulse.regime import analog, inputs as inputs_mod
    from apps.market_pulse.regime.category import categorize_or_none, categorize_regime
    from apps.market_pulse.regime.inputs import ALL_INPUT_KEYS
    from apps.market_pulse.regime.zscore import compute_baseline
    from macro.models.indicators import MarketIndex, MarketIndexPrice

    # 모집단(완전벡터 소급) + S4 잣대 baseline 재사용.
    pop_rows = list(
        RegimeSnapshot.objects.filter(summary=BACKFILL_MARK, coverage__gte=1.0)
        .order_by("date")
        .values_list("date", "inputs")
    )
    if not pop_rows:
        return {"available": False}
    baseline = compute_baseline([inp for _, inp in pop_rows], ALL_INPUT_KEYS)
    weights = analog.component_weights()

    # L2 카테고리(C-core): 이웃일 date → regime 확정치. 결정론 파생(저장 0).
    regime_by_date = dict(
        RegimeSnapshot.objects.filter(summary=BACKFILL_MARK, coverage__gte=1.0)
        .values_list("date", "regime")
    )

    # 오늘 벡터(as_of=오늘, 소급과 동형 문법) → z.
    today = _tz.localdate()
    today_z = analog.to_z(inputs_mod.load_inputs(as_of=today).as_dict(), baseline)

    population = [(d, analog.to_z(inp, baseline)) for d, inp in pop_rows]
    neighbors, nearest = analog.select_neighbors(today_z, population, weights)
    alert_on = analog.is_alert(nearest)

    # SPY 선도수익용 거래일 캘린더(주말 제외 — 비거래일 15행이 T+n 조인에 새지 않게).
    spy = MarketIndex.objects.filter(symbol="SPY").first()
    closes_rows = (
        list(
            MarketIndexPrice.objects.filter(index=spy)
            .exclude(close__isnull=True)
            .order_by("date")
            .values_list("date", "close")
        )
        if spy
        else []
    )
    trading = [(d, float(c)) for d, c in closes_rows if d.weekday() < 5]
    price_index = {d: i for i, (d, _) in enumerate(trading)}
    closes = [c for _, c in trading]

    # L3 맥락(C-L3): 이웃일 date → 저장분 read(렌더 LLM 0). 단일 쿼리(N+1 방지).
    ctx_by_date = {
        c.date: c
        for c in AnalogDayContext.objects.filter(date__in=[nb["date"] for nb in neighbors])
    }

    neighbor_out = []
    neighbor_fwd = []
    for nb in neighbors:
        fwd = analog.forward_returns(nb["date"], price_index, closes)
        cat = categorize_or_none(regime_by_date.get(nb["date"]))  # L2(C-core): 그날 국면 유형
        ctx = ctx_by_date.get(nb["date"])  # L3(C-L3): 저장분(없으면 why=null)
        neighbor_out.append({
            "date": nb["date"].isoformat(),
            "dist": nb["dist"],
            "cat_slot": cat["label"] if cat else None,  # 사실 분류 표기(string 계약 유지)
            "cat_key": cat["key"] if cat else None,     # FE 톤용 RegimeId(additive)
            "why": ctx.why_text if ctx else None,       # L3 맥락 1문장(저장분 read, 미생성=null)
            "why_provenance": ctx.provenance if ctx else None,  # 근거 헤드라인 [{id,url,title}]
            "why_version": ctx.prompt_version if ctx else None,  # 생성 프롬프트 버전
            "fwd": {str(h): v for h, v in fwd.items()},
        })
        neighbor_fwd.append({"date": nb["date"], "fwd": fwd})

    fan = analog.build_fan(neighbor_fwd, k=len(neighbors))

    # 오늘 국면 4 유효 축(z 막대): 가족 평균 z + 단독.
    def _axis_z(keys):
        zs = [today_z[k] for k in keys if k in today_z]
        return round(sum(zs) / len(zs), 3) if zs else None

    today_axes = [
        {"axis": "stress", "z": _axis_z(analog.REGIME_FAMILIES["stress"])},
        {"axis": "financial", "z": _axis_z(analog.REGIME_FAMILIES["financial"])},
        {"axis": "return_1d_pct", "z": _axis_z(("return_1d_pct",))},
        {"axis": "vol_20d_pct", "z": _axis_z(("vol_20d_pct",))},
    ]

    # 오늘 국면 태그(가능 시): 라이브 스냅샷 regime 확정치가 status OK일 때만(사실 표기).
    today_snap = (
        RegimeSnapshot.objects.filter(date=today, status=RegimeSnapshot.Status.OK)
        .order_by("-snapshot_time")
        .first()
    )
    today_category = categorize_regime(today_snap.regime) if today_snap and today_snap.regime else None

    return {
        "available": True,
        "as_of": today.isoformat(),
        "today_axes": today_axes,
        "today_category": today_category,
        "neighbors": neighbor_out,
        "fan": fan,
        "alert": {"on": alert_on, "nearest_dist": round(nearest, 4) if nearest is not None else None},
        "meta": {
            "k_max": analog.K_MAX,
            "tau_radius": analog.TAU_RADIUS,
            "tau_alert": analog.TAU_ALERT,
            "horizons": list(analog.HORIZONS),
            "population": len(pop_rows),
            "spy_trading_days": len(trading),
        },
    }


_BREADTH_MA_WINDOW = 20
_BREADTH_DISPLAY = 30


def _breadth_detail():
    snap = BreadthSnapshot.objects.filter(universe="SPY").order_by("-date").first()
    if snap is None:
        return {"available": False}
    # MP2-TREND S2: MA20 파생을 위해 표시 30일 + 룩백 19일 = 49일 조회(조회-시 파생, 저장 0).
    #   최근 30일 전 구간의 기준선까지 채우려면 window-1 만큼 더 필요. 깊이 부족 시 앞구간 None.
    lookback = _BREADTH_DISPLAY + _BREADTH_MA_WINDOW - 1
    raw = list(
        BreadthSnapshot.objects.filter(universe="SPY")
        .order_by("-date")[:lookback]
        .values("date", "advance_count", "decline_count", "ad_line", "ad_line_change")
    )
    raw.reverse()  # 과거→현재
    ad_series = [h["ad_line"] for h in raw]
    ma_full = _sma_series(ad_series, _BREADTH_MA_WINDOW)
    # 표시 구간 = 마지막 30일(+ 대응 MA 슬라이스)
    display = raw[-_BREADTH_DISPLAY:]
    ma_display = ma_full[-_BREADTH_DISPLAY:]
    streak = _deviation_streak(
        [h["ad_line"] for h in display], ma_display
    )
    return {
        "available": True,
        "universe": snap.universe,
        "date": snap.date.isoformat(),
        "advance": snap.advance_count,
        "decline": snap.decline_count,
        "unchanged": snap.unchanged_count,
        "total": snap.total_count,
        "new_high_52w": snap.new_high_52w,
        "new_low_52w": snap.new_low_52w,
        "ad_line": snap.ad_line,
        "ad_line_change": snap.ad_line_change,
        # MP2-TREND S2(additive): 최신일 기준 기준선(MA20) 이탈 연속 일수.
        "ma_deviation_streak_days": streak,
        "history_30d": [
            {
                "date": h["date"].isoformat(),
                "advance": h["advance_count"],
                "decline": h["decline_count"],
                "ad_line": h["ad_line"],
                "ad_line_change": h["ad_line_change"],
                # MP2-TREND S2(additive): A/D선 20일 이동평균(기준선). <20일 구간은 null.
                "ad_line_ma20": ma_display[i],
            }
            for i, h in enumerate(display)
        ],
    }


def _sector_detail():
    rows = list(SectorFlowSnapshot.objects.order_by("-date"))
    if not rows:
        return {"available": False}
    latest_date = rows[0].date
    latest = sorted(
        [r for r in rows if r.date == latest_date], key=lambda r: r.rank_in_universe
    )

    # CD-STAB Slice A′(D-CD-XAXIS-SCOPE): 판단 x축 = 5일 상대수익(mom5 − bench5d).
    #   벤치 5일 수익률을 거래일별로 1회 파생(서빙 시점, 저장 0). rel_strength_5d = 이 값을
    #   섹터 momentum_5d에서 뺀 값 — 판단 계열(classify·리플레이·RRG·카드) 단일 입력.
    bench_5d = _bench_5d_return_by_date()

    def _rel5(r):
        return derive_rel_strength_5d(r.momentum_5d, bench_5d.get(r.date))

    # MP-UX-S5-B-SECTOR-BE: 섹터별 rel_strength 시계열 (additive, breadth/concentration
    #   history_30d 패턴 미러 — 단 섹터×날짜 2-D, rel_strength only). SectorFlowSnapshot
    #   실데이터만(합성 0): 결측·미존재 채우지 않음. 11섹터 전부 반환(절단은 FE slice 2).
    recent_dates = []
    _seen_dates = set()
    for r in rows:  # rows: -date 정렬 → 최근 distinct 날짜 ≤30
        if r.date not in _seen_dates:
            _seen_dates.add(r.date)
            recent_dates.append(r.date)
            if len(recent_dates) >= 30:
                break
    recent_set = set(recent_dates)
    per_symbol: dict = {}
    for r in sorted(rows, key=lambda x: x.date):  # date 오름차순 누적
        if r.date in recent_set and r.rel_strength is not None:  # 결측 skip(0 변환 0)
            per_symbol.setdefault(r.market_index_id, []).append(
                # MP2-TREND S1(additive): rank 노출 — 순위 궤적 y축(1위 상단). rel_strength는 리드아웃 부기용 유지.
                {
                    "date": r.date.isoformat(),
                    "rel_strength": float(r.rel_strength),
                    "rank": r.rank_in_universe,
                    # MP2-SECTOR-CD S2(additive): per-date momentum_5d 노출 — 저장값 그대로(재계산 0).
                    #   초기 룩백 등 저장 null은 null 그대로 서빙(보간·발명 금지).
                    "momentum_5d": (
                        float(r.momentum_5d) if r.momentum_5d is not None else None
                    ),
                    # CD-STAB Slice A′(additive): per-date 5일 상대수익 — RRG 점/꼬리 x축(판단 계열).
                    #   bench 소급 부족 날은 null 그대로(발명 금지). 기존 rel_strength(1일)는 그대로 유지.
                    "rel_strength_5d": (
                        float(rel5) if (rel5 := _rel5(r)) is not None else None
                    ),
                }
            )
    ordered_symbols = [r.market_index_id for r in latest]  # sectors[]와 동일 rank 순
    for sym in per_symbol:
        if sym not in ordered_symbols:
            ordered_symbols.append(sym)
    sector_history = [
        {"symbol": sym, "history": per_symbol.get(sym, [])}  # 데이터 없는 섹터 → []
        for sym in ordered_symbols
    ]

    # CD-STAB Slice B(D-CD-STAB): 공식 cd_state = 2일 히스테리시스 리플레이(무상태).
    #   입력 = 섹터별 전 구간 distinct 거래일 raw 상태 시퀀스(ORM 전 구간, 30일 서빙 캡 무관).
    #   현재 공식 상태 = 리플레이 마지막 원소. 저장 0 — 매 서빙 시 결정론적 재생.
    # CD-STAB Slice A′(D-CD-XAXIS-SCOPE): 리플레이 입력 x = rel_strength_5d(5일 상대수익).
    #   cd_state·cd_state_raw가 일괄 5d 체계로 전환. bench 소급 부족 날 = rel5 None →
    #   classify None → resolve의 None 방어(후보 리셋·공식 유지) 그대로 적용(규칙 #5).
    raw_seq_by_symbol: dict = {}
    for r in sorted(rows, key=lambda x: x.date):  # 오름차순
        raw_seq_by_symbol.setdefault(r.market_index_id, []).append(
            classify_cd_state(_rel5(r), r.momentum_5d)
        )
    official_by_symbol = {
        sym: resolve_official_cd_state(seq)[-1]
        for sym, seq in raw_seq_by_symbol.items()
    }

    return {
        "available": True,
        "date": latest_date.isoformat(),
        "sectors": [
            {
                "symbol": r.market_index_id,
                "rel_strength": float(r.rel_strength),
                # CD-STAB Slice A′(additive): 5일 상대수익 — 판단 계열 x축(RRG 점·미니맵·카드 근거).
                #   기존 rel_strength(1일)는 맥박 계열(히트맵 등)이 그대로 소비(무접촉, 규칙 #1).
                #   bench 소급 부족 시 null(발명 금지).
                "rel_strength_5d": (
                    float(rel5) if (rel5 := _rel5(r)) is not None else None
                ),
                "momentum_1d": float(r.momentum_1d),
                "momentum_5d": float(r.momentum_5d),
                "momentum_20d": float(r.momentum_20d),
                "flow_proxy": float(r.flow_proxy),
                "rank": r.rank_in_universe,
                # MP2-SECTOR-CD S1 → CD-STAB Slice B(D-CD-STATE-SEMANTICS) → A′(D-CD-XAXIS-SCOPE):
                #   판단 4-상태. cd_state = 공식(2일 히스테리시스 확정, 입력 x=5일 상대수익) 상태 —
                #   전 소비자(뱃지·점색·문구)가 소비. FE·2차 소비자는 재계산 금지. None → 판단 유보.
                "cd_state": official_by_symbol.get(r.market_index_id),
                # cd_state_raw(additive): 원시 즉시 분류값(입력 x=5일 상대수익). "전환 확인 중" 표시 등 후속 소비용.
                "cd_state_raw": classify_cd_state(_rel5(r), r.momentum_5d),
            }
            for r in latest
        ],
        "cross_dispersion": float(latest[0].cross_dispersion),
        "rotation_index": float(latest[0].rotation_index),
        "sector_history": sector_history,
        # MP2-SECTOR-CD S2(additive): 모멘텀 판정선 단일소스. FE가 y=0 하드코딩 금지 —
        #   이 서빙값(= CD_MOMENTUM_BASELINE 상수)을 hline으로 그린다. 값 복제 아님(import 참조).
        "cd_momentum_baseline": CD_MOMENTUM_BASELINE,
        # MP2-SECTOR-CD S3(additive): RRG x축(상대강도) 판정선 단일소스. FE 하드코딩 금지 —
        #   서빙값(= CD_REL_STRENGTH_BASELINE 상수)을 수직 기준선으로 그린다. cd_momentum_baseline과 동형.
        "cd_rel_strength_baseline": CD_REL_STRENGTH_BASELINE,
    }


def _concentration_detail():
    snap = ConcentrationSnapshot.objects.order_by("-date").first()
    if snap is None:
        return {"available": False}
    history = list(
        ConcentrationSnapshot.objects.order_by("-date")[:30].values(
            "date", "top5_weight", "top10_weight", "hhi"
        )
    )
    history.reverse()
    return {
        "available": True,
        "date": snap.date.isoformat(),
        "universe": snap.universe,
        "top5_weight": float(snap.top5_weight),
        "top10_weight": float(snap.top10_weight),
        "hhi": float(snap.hhi),
        "top_holdings": snap.top_holdings or [],
        "history_30d": [
            {
                "date": h["date"].isoformat(),
                "top5": float(h["top5_weight"]),
                "top10": float(h["top10_weight"]),
                "hhi": float(h["hhi"]),
            }
            for h in history
        ],
    }


def _brief_detail():
    log = BriefingLog.objects.order_by("-date").first()
    if log is None:
        return {"available": False}
    return {
        "available": True,
        "date": log.date.isoformat(),
        "model_version": log.model_version,
        "status": log.status,
        "headline": log.headline,
        "body": log.body,
        "body_sections": log.body_sections or [],
        "prompt_inputs": log.prompt_inputs,
        "tokens": {
            "prompt": log.prompt_tokens,
            "completion": log.completion_tokens,
            "latency_ms": log.latency_ms,
        },
    }
