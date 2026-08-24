"""D1-SCOREBOARD Part 1 — 애널리스트 성적판 read API (compute-on-read + 나안 TTL 캐시).

GET /api/v1/coach/analyst-scorecard/?h=21

전역 read 스코프: user 필터 없음(모든 AnalystSignalSnapshot 대상). 인증만 요구
(IsAuthenticated — coach 표면 권한 통일 #70 정합, D-I3-1 파생 계산·신규 테이블 0).
DB 쓰기 0. 채점 코어는 packages.shared.stocks.services.analyst_scoring 순수 함수
재사용(command 산출 byte-IDENTICAL 보존 — 기존 집계 함수 무접촉).
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from packages.shared.stocks.models import AnalystSignalSnapshot, DailyPrice, StockSplit
from packages.shared.stocks.services import analyst_scoring as sc

# 나안 캐시(결정 3): 계산 지연 상한 선확보. 입력 최신일 3좌표를 키에 포함해
# 데이터 갱신 시 키 회전(stale 구조적 불가). TTL 24h로 as_of 드리프트 상한.
SCORECARD_CACHE_TTL = 60 * 60 * 24  # 24h
_H_MIN, _H_MAX = 1, 504  # 지평 거래일 상한(≈2년) — 무리한 입력 방어


class AnalystScorecardSerializer(serializers.Serializer):
    """스키마 앵커(passthrough) — 실 스키마는 compute-on-read dict 계약."""

    def to_representation(self, instance):
        return instance


def scorecard_cache_key(h: int) -> str:
    """캐시 키 = {SCORING_VERSION, h, 입력 최신일 3좌표}.

    snapshot·DailyPrice·StockSplit 각 max date가 키에 포함되므로 데이터가 갱신되면
    키가 회전 → 낡은 payload 반환 구조적 불가. computed_at으로 hit/재계산 구분.
    """
    ass_max = AnalystSignalSnapshot.objects.aggregate(m=Max("captured_at"))["m"]
    dp_max = DailyPrice.objects.aggregate(m=Max("date"))["m"]
    sp_max = StockSplit.objects.aggregate(m=Max("date"))["m"]
    ass_s = ass_max.date().isoformat() if ass_max else "none"
    return f"scoreboard:v{sc.SCORING_VERSION}:h{h}:{ass_s}:{dp_max or 'none'}:{sp_max or 'none'}"


@extend_schema(
    responses={200: AnalystScorecardSerializer},
    tags=["portfolio-advisory"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analyst_scorecard(request: Request) -> Response:
    """애널리스트 성적판(전역 read). `?h=` 거래일 지평(기본 21).

    스코프: **전역**(모든 신호) — user 필터 없음(#95: 스코프는 선언). 모든 인증
    사용자에게 동일 산출. compute-on-read(DB 쓰기 0) + 나안 TTL 캐시.
    """
    raw = request.query_params.get("h", "21")
    try:
        h = int(raw)
    except (TypeError, ValueError):
        return Response({"detail": "h must be an integer"}, status=400)
    if not (_H_MIN <= h <= _H_MAX):
        return Response({"detail": f"h out of range [{_H_MIN}, {_H_MAX}]"}, status=400)

    key = scorecard_cache_key(h)
    payload = cache.get(key)
    if payload is None:
        as_of = timezone.localdate()
        payload = sc.build_scorecard(as_of, h)
        payload["reproduction"]["computed_at"] = timezone.now().isoformat()
        cache.set(key, payload, SCORECARD_CACHE_TTL)
    return Response(payload)


urlpatterns = []  # 라우팅은 api/urls.py에서 명시(가시성). 여기선 뷰만 노출.
