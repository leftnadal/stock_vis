"""
credit_signals read API (PR §7).

GET /api/credit-signals/strip/
    Dashboard용 크레딧 신호 스트립. read-only, 인증은 전역 기본(IsAuthenticated)
    상속 — 파생 자산이므로 AllowAny 금지 (audit P0 #5 정책).

N+1 금지: 상태 1쿼리 + 시리즈별 spark 단일 쿼리(6개). 총 쿼리 수 상한 고정.
"""
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from ..constants import FRED_SERIES, SIGNAL_SERIES_MAP
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


class CreditSignalStripView(APIView):
    """크레딧 신호 스트립 (as_of + 6개 signal + spark)."""

    @extend_schema(tags=["Credit Signals"], summary="크레딧 신호 스트립 (Dashboard)")
    def get(self, request):
        states = {
            s.signal_key: s
            for s in CreditSignalState.objects.filter(
                signal_key__in=SIGNAL_SERIES_MAP.keys()
            )
        }

        signals = []
        as_of = None
        for signal_key, series_id in SIGNAL_SERIES_MAP.items():
            state = states.get(signal_key)
            if state is None:
                continue
            if as_of is None or state.as_of > as_of:
                as_of = state.as_of
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

        return Response(
            {
                "as_of": as_of.isoformat() if as_of else None,
                "signals": signals,
            }
        )
