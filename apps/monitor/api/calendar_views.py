"""이벤트 캘린더 API (EVT-IMPL-4 STEP 2-1).

GET /api/v1/monitor/calendar/ — 연합 읽기 피드(EventFeed). IsAuthenticated·user 스코프.
읽기 전용. 범위 상한 120일(초과 400). 응답 = build_event_feed 결과 그대로.
"""
from __future__ import annotations

import datetime as _dt
import re
from zoneinfo import ZoneInfo

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.monitor.services.chain_feed import build_chain_feed
from apps.monitor.services.event_feed import build_event_feed

_ET = ZoneInfo("America/New_York")
_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_ALLOWED_KINDS = {"holiday", "macro", "earnings", "dividend", "split", "split_effective"}
_ALLOWED_SCOPE = {"monitor", "watchlist", "both"}
_ALLOWED_IMPORTANCE = {"critical", "high", "medium", "low"}
_MAX_SPAN_DAYS = 120


def _parse_date(raw: str | None):
    if not raw:
        return None
    return _dt.date.fromisoformat(raw)  # ValueError → 상위에서 400


def _parse_bool(raw: str | None) -> bool:
    return str(raw).lower() in ("1", "true", "yes", "on")


class CalendarFeedView(APIView):
    """GET /api/v1/monitor/calendar/ — 관심종목 4원천 연합 이벤트 피드.

    쿼리: from(기본 ET−7) · to(기본 +90, 창 상한 120일) · scope(monitor|watchlist|both) ·
    kinds(csv) · include_stale(bool) · macro_min_importance(critical|high|medium|low).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        et_today = _dt.datetime.now(tz=_ET).date()
        try:
            start = _parse_date(request.query_params.get("from")) or (et_today - _dt.timedelta(days=7))
            end = _parse_date(request.query_params.get("to")) or (et_today + _dt.timedelta(days=90))
        except ValueError:
            return Response({"detail": "from/to 는 YYYY-MM-DD 형식이어야 합니다."},
                            status=status.HTTP_400_BAD_REQUEST)
        if end < start:
            return Response({"detail": "to 는 from 이후여야 합니다."},
                            status=status.HTTP_400_BAD_REQUEST)
        if (end - start).days > _MAX_SPAN_DAYS:
            return Response({"detail": f"조회 범위는 최대 {_MAX_SPAN_DAYS}일입니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        scope = request.query_params.get("scope", "monitor")
        if scope not in _ALLOWED_SCOPE:
            return Response({"detail": f"scope 는 {sorted(_ALLOWED_SCOPE)} 중 하나여야 합니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        importance = request.query_params.get("macro_min_importance", "high")
        if importance not in _ALLOWED_IMPORTANCE:
            return Response({"detail": f"macro_min_importance 는 {sorted(_ALLOWED_IMPORTANCE)} 중 하나여야 합니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        kinds_raw = request.query_params.get("kinds")
        kinds = None
        if kinds_raw:
            kinds = {k.strip() for k in kinds_raw.split(",") if k.strip()}
            bad = kinds - _ALLOWED_KINDS
            if bad:
                return Response({"detail": f"알 수 없는 kind: {sorted(bad)}"},
                                status=status.HTTP_400_BAD_REQUEST)

        include_stale = _parse_bool(request.query_params.get("include_stale"))

        feed = build_event_feed(
            request.user, start=start, end=end, scope=scope, kinds=kinds,
            include_stale=include_stale, macro_min_importance=importance,
        )
        return Response(feed)


class CalendarChainView(APIView):
    """GET /api/v1/monitor/calendar/chain/?symbol= — 관계망 이벤트 피드(EVT-CHAIN-1).

    시드 심볼의 1-hop 관계 이웃(RelationConfidence confirmed·truth≥임계·top-k) 어닝 타임라인
    + 시드 자신의 다가오는 이벤트(위젯). 읽기 전용·부호 중립. 미존재 심볼 = 빈 응답(404 아님).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        symbol = (request.query_params.get("symbol") or "").strip().upper()
        if not symbol:
            return Response({"detail": "symbol 파라미터가 필요합니다."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not _SYMBOL_RE.match(symbol):
            return Response({"detail": "symbol 형식이 올바르지 않습니다(대문자 심볼)."},
                            status=status.HTTP_400_BAD_REQUEST)
        feed = build_chain_feed(request.user, symbol)
        return Response(feed)
