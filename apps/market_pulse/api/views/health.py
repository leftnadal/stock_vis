"""
Health endpoint (PR-J, Admin only).

소속: apps/market_pulse/api/views (app 레이어 DRF Views).
역할: 4 스냅샷 마지막 갱신 시각·status·coverage·캐시 상태 응답.
권한: IsAdminUser — 운영 점검용. 일반 사용자 노출 금지.
"""

from __future__ import annotations

import time

from django.core.cache import cache
from django.db import connection
from django.utils import timezone as django_timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_pulse.api import cache as cache_keys
from apps.market_pulse.models.briefing import BriefingLog
from apps.market_pulse.models.news import MarketPulseNews
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)


def _check_db():
    started = time.time()
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
            c.fetchone()
        return True, int((time.time() - started) * 1000)
    except Exception:
        return False, int((time.time() - started) * 1000)


def _check_cache():
    started = time.time()
    try:
        cache.set("mp:health:probe", "pong", timeout=10)
        ok = cache.get("mp:health:probe") == "pong"
        return ok, int((time.time() - started) * 1000)
    except Exception:
        return False, int((time.time() - started) * 1000)


def _last_runs():
    def _ts(model, field="created_at"):
        obj = model.objects.order_by(f"-{field}").first()
        return obj and getattr(obj, field).isoformat() or None

    return {
        "news_last_fetched": _ts(MarketPulseNews, "fetched_at"),
        "regime_last_snapshot": _ts(RegimeSnapshot, "snapshot_time"),
        "breadth_last_snapshot": _ts(BreadthSnapshot, "snapshot_time"),
        "concentration_last_snapshot": _ts(ConcentrationSnapshot, "snapshot_time"),
        "sector_last_snapshot": _ts(SectorFlowSnapshot, "snapshot_time"),
        "briefing_last": _ts(BriefingLog, "created_at"),
    }


@extend_schema(
    summary="Admin 전용 health probe",
    description="DB ping + cache ping + 마지막 task 실행 시각.",
    tags=["Market Pulse v2"],
    responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
)
class HealthView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        cached = cache.get(cache_keys.health_key())
        if cached is not None:
            cached["_meta"]["cache"] = "HIT"
            return Response(cached)

        db_ok, db_ms = _check_db()
        cache_ok, cache_ms = _check_cache()
        payload = {
            "_meta": {
                "generated_at": django_timezone.now().isoformat(),
                "cache": "MISS",
            },
            "probes": {
                "db": {"ok": db_ok, "latency_ms": db_ms},
                "cache": {"ok": cache_ok, "latency_ms": cache_ms},
            },
            "last_runs": _last_runs(),
        }
        cache.set(cache_keys.health_key(), payload, timeout=cache_keys.HEALTH_TTL_SEC)
        return Response(payload)
