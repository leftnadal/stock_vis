"""iron-trading read-only API views."""

from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.daily_context import (
    BadRequest,
    SnapshotBuilding,
    SnapshotNotFound,
    build_daily_context,
    error_body,
    parse_query,
)


class DailyContextView(APIView):
    """GET /api/v1/iron-trading/daily-context

    read-only. iron_trading 외부 봇이 일별 결정보드 입력을 받기 위해 호출.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        try:
            params = parse_query(
                request.query_params.get("date"),
                request.query_params.get("universe"),
                request.query_params.get("limit"),
            )
        except BadRequest as exc:
            return Response(error_body(exc.code, exc.message), status=400)

        try:
            payload = build_daily_context(params)
        except SnapshotNotFound as exc:
            return Response(error_body("snapshot_not_found", exc.message), status=404)
        except SnapshotBuilding as exc:
            response = Response(
                error_body("snapshot_not_ready", exc.message, exc.retry_after_seconds),
                status=503,
            )
            response["Retry-After"] = str(exc.retry_after_seconds)
            return response

        return Response(payload, status=200)
