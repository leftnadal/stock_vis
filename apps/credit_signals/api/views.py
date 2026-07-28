"""
credit_signals read API (PR §7).

GET /api/credit-signals/strip/
    Dashboard용 크레딧 신호 스트립. read-only, 인증은 전역 기본(IsAuthenticated)
    상속 — 파생 자산이므로 AllowAny 금지 (audit P0 #5 정책).

N+1 금지: 상태 1쿼리 + raw spark 6쿼리 + 파생 spark 2×2쿼리 = 상한 11쿼리 고정.
"""
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from ..constants import (
    DERIVED_SERIES,
    DERIVED_SIGNAL_MAP,
    FRED_SERIES,
    SIGNAL_SERIES_MAP,
)
from ..models import CreditSignalState, MacroSeriesHistory

SPARK_POINTS = 30  # spark = 최근 30 관측치


def _spark(series_id: str) -> list:
    """시리즈별 최근 SPARK_POINTS 관측치 (오름차순). 시리즈당 단일 쿼리."""
    rows = list(
        MacroSeriesHistory.objects.filter(series_id=series_id)
        .order_by("-date")
        .values_list("date", "value")[:SPARK_POINTS]
    )
    rows.reverse()  # 오래된 → 최신
    return [{"date": d.isoformat(), "value": float(v)} for d, v in rows]


def _spark_derived(key: str) -> list:
    """파생키 spark = 두 시리즈 최근 정합 SPARK_POINTS점의 스프레드 (2쿼리)."""
    minuend_id, subtrahend_id = DERIVED_SIGNAL_MAP[key]
    # 최근 2×SPARK_POINTS를 각각 받아 inner-join 후 마지막 SPARK_POINTS점 사용
    # (결측 흡수 여유). 정합 완전 시 상위 SPARK_POINTS와 동일.
    m = dict(
        MacroSeriesHistory.objects.filter(series_id=minuend_id)
        .order_by("-date")
        .values_list("date", "value")[: SPARK_POINTS * 2]
    )
    s = dict(
        MacroSeriesHistory.objects.filter(series_id=subtrahend_id)
        .order_by("-date")
        .values_list("date", "value")[: SPARK_POINTS * 2]
    )
    common = sorted(set(m) & set(s))[-SPARK_POINTS:]
    return [{"date": d.isoformat(), "value": float(m[d] - s[d])} for d in common]


class CreditSignalStripView(APIView):
    """크레딧 신호 스트립 (as_of + raw 6 + 파생 2 signal + spark)."""

    @extend_schema(tags=["Credit Signals"], summary="크레딧 신호 스트립 (Dashboard)")
    def get(self, request):
        keys = list(SIGNAL_SERIES_MAP) + list(DERIVED_SIGNAL_MAP)
        states = {
            s.signal_key: s
            for s in CreditSignalState.objects.filter(signal_key__in=keys)
        }

        signals = []
        as_of = None

        def _touch_as_of(state):
            nonlocal as_of
            if as_of is None or state.as_of > as_of:
                as_of = state.as_of

        # raw 6
        for signal_key, series_id in SIGNAL_SERIES_MAP.items():
            state = states.get(signal_key)
            if state is None:
                continue
            _touch_as_of(state)
            signals.append(
                {
                    "key": signal_key,
                    "name": FRED_SERIES[series_id]["name"],
                    "value": float(state.value),
                    "z": None if state.z_score is None else float(state.z_score),
                    "grade": state.grade,
                    "spark": _spark(series_id),
                }
            )

        # 파생 2 (raw 뒤 — 정렬은 프론트 프리젠테이션 담당)
        for key in DERIVED_SIGNAL_MAP:
            state = states.get(key)
            if state is None:
                continue
            _touch_as_of(state)
            signals.append(
                {
                    "key": key,
                    "name": DERIVED_SERIES[key]["name"],
                    "value": float(state.value),
                    "z": None if state.z_score is None else float(state.z_score),
                    "grade": state.grade,
                    "spark": _spark_derived(key),
                }
            )

        return Response(
            {
                "as_of": as_of.isoformat() if as_of else None,
                "signals": signals,
            }
        )
