"""
Card Detail endpoints (PR-J).

소속: apps/market_pulse/api/views (app 레이어 DRF Views).
역할: 4 카드 디테일 엔드포인트(Regime/Breadth/Sector/Concentration) — 시계열 또는
  세부 메트릭 응답. cache.py 키 빌더로 Redis 캐시.
소비처: 마켓 펄스 화면 카드 드릴다운.
"""

from __future__ import annotations

import time
from typing import Any

from django.core.cache import cache
from django.utils import timezone as django_timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_pulse.api import cache as cache_keys
from apps.market_pulse.constants import (
    CD_MOMENTUM_BASELINE,
    CD_REL_STRENGTH_BASELINE,
    classify_cd_state,
)
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

VALID_CARDS = {"regime", "breadth", "sector", "concentration", "brief"}


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

    return {
        "available": True,
        "date": latest_date.isoformat(),
        "sectors": [
            {
                "symbol": r.market_index_id,
                "rel_strength": float(r.rel_strength),
                "momentum_1d": float(r.momentum_1d),
                "momentum_5d": float(r.momentum_5d),
                "momentum_20d": float(r.momentum_20d),
                "flow_proxy": float(r.flow_proxy),
                "rank": r.rank_in_universe,
                # MP2-SECTOR-CD S1(additive): 판단 4-상태. 판정 로직 단일소스(payload builder).
                #   FE·2차 소비자는 재계산 금지 — 이 값만 표시. None → 판단 유보.
                "cd_state": classify_cd_state(r.rel_strength, r.momentum_5d),
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
