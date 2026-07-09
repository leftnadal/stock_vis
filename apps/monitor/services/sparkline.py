"""상태밴드 스파크라인 score 시계열 (MON-P3-ALERT §6, read-only).

MonitorSnapshot이 불충분할 때(초기 2건) 스파크라인을 렌더할 수 있도록, IndicatorReading에서
거래일별 overall_score를 **읽기 전용으로 재계산**한다(스냅샷 쓰기·상태 변경 없음 →
evaluate-replay 백필의 과거 전이 알림 오발 회피, §0.2 결정).

상태 구간 임계값은 엔진의 `score_to_phase` 경계를 단일 출처로 하달(FE 하드코딩 금지).
Δ5d는 계산만 준비하고 표시는 회전 맵 트랙 몫(결정 1b).
"""
from apps.monitor.models import AlertEvent
from apps.monitor.services.indicator_scorer import score_indicator_from_model
from apps.monitor.services.monitor_aggregator import aggregate_monitor

WINDOW_DEFAULT = 30  # 최근 거래일 수

# score_to_phase(state_machine) 경계와 동기화된 상태 밴드(높은 score→밝은 위상).
# FE는 이 값으로 색 밴드를 그린다(하드코딩 금지). 상·하한은 score 정의역 [-1, 1].
SCORE_BANDS = [
    {"phase": "full_moon", "label": "가설이 빛나고 있어요", "min": 0.6, "max": 1.0},
    {"phase": "waxing", "label": "조금씩 밝아지고 있어요", "min": 0.2, "max": 0.6},
    {"phase": "half_moon", "label": "반반이에요", "min": -0.2, "max": 0.2},
    {"phase": "waning", "label": "조금씩 어두워지고 있어요", "min": -0.6, "max": -0.2},
    {"phase": "new_moon", "label": "가설이 힘을 잃고 있어요", "min": -1.0, "max": -0.6},
]


def _trading_asofs(monitor):
    """모니터 active 지표들의 reading asof(거래일) 오름차순 distinct 목록."""
    dates = set()
    for ind in monitor.indicators.filter(is_active=True):
        for asof in ind.readings.filter(
            validation_status__in=["ok", "extreme_jump_allowed"]
        ).values_list("asof", flat=True):
            dates.add(asof.date() if hasattr(asof, "date") else asof)
    return sorted(dates)


def _overall_at(monitor, indicators, as_of):
    """as_of 시점 overall_score(읽기 전용). evaluate의 스코어 단계만 재현."""
    scores = {
        str(ind.id): score_indicator_from_model(ind, as_of_date=as_of)["score"]
        for ind in indicators
    }
    return aggregate_monitor(monitor, scores)["overall_score"]


def score_series(monitor, window=WINDOW_DEFAULT):
    """최근 `window` 거래일 score 시계열 + 상태 밴드 + 전이 표식 + Δ5d.

    반환: {
        "series": [{"asof": iso, "score": float}, ...],   # 시간 오름차순
        "bands": SCORE_BANDS,
        "transitions": [iso, ...],                          # 그 창의 AlertEvent asof
        "delta_5d": float|None,                             # 계산만(표시는 회전 맵 트랙)
        "window": int,
    }
    """
    indicators = list(monitor.indicators.filter(is_active=True))
    asofs = _trading_asofs(monitor)[-window:]

    series = [
        {"asof": d.isoformat(), "score": _overall_at(monitor, indicators, d)}
        for d in asofs
    ]

    transition_asofs = set(
        AlertEvent.objects.filter(
            monitor=monitor, asof__gte=asofs[0] if asofs else None
        ).values_list("asof", flat=True)
    ) if asofs else set()
    transitions = sorted(a.isoformat() for a in transition_asofs)

    delta_5d = None
    if len(series) >= 6:
        delta_5d = round(series[-1]["score"] - series[-6]["score"], 4)

    return {
        "series": series,
        "bands": SCORE_BANDS,
        "transitions": transitions,
        "delta_5d": delta_5d,
        "window": window,
    }
