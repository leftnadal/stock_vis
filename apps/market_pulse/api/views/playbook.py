"""Macro Playbook API (1.6-S1 / D-P16-ENGINE) — compute-on-read.

GET /api/v2/market-pulse/playbook → 봉투(data = build_payload). 판단·상태·서사는 BE(engine)
단일소스, FE는 표시만. anomaly와 분리된 playbook 모듈만 소비(anomaly 무접촉).
"""

from __future__ import annotations

import time

from django.core.cache import cache
from django.utils import timezone as django_timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_pulse.api.views.cards import _envelope
from apps.market_pulse.playbook.engine import build_payload
from apps.market_pulse.throttles import MarketPulseHourThrottle, MarketPulseUserThrottle

_PLAYBOOK_TTL_SEC = 300


class PlaybookView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def get(self, request, *args, **kwargs):
        started = time.time()
        today = django_timezone.localdate()
        key = f"marketpulse:playbook:{today.isoformat()}"
        try:
            cached = cache.get(key)
        except Exception:  # pragma: no cover - 캐시 장애 폴백
            cached = None
        if cached is not None:
            return Response(_envelope(cached, started, cache_state="HIT"))

        payload = build_payload()
        try:
            cache.set(key, payload, timeout=_PLAYBOOK_TTL_SEC)
        except Exception:  # pragma: no cover
            pass
        return Response(_envelope(payload, started, cache_state="MISS"))
