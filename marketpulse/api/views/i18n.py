"""Market Pulse v2 — i18n endpoint (PR-J)."""

from __future__ import annotations

from django.core.cache import cache
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marketpulse.api import cache as cache_keys
from marketpulse.i18n import labels as labels_mod
from marketpulse.throttles import MarketPulseHourThrottle, MarketPulseUserThrottle


@extend_schema(
    summary="영문 키 → 한글 라벨 lookup",
    tags=["Market Pulse v2"],
    parameters=[
        OpenApiParameter(name="locale", type=str, default="ko"),
    ],
    responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
)
class I18nView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarketPulseUserThrottle, MarketPulseHourThrottle]

    def get(self, request, *args, **kwargs):
        locale = request.query_params.get("locale", "ko").lower()
        key = cache_keys.i18n_key(locale)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)

        payload = {
            "_meta": {
                "locale": locale,
                "supported": labels_mod.supported_locales(),
                "cache": "MISS",
            },
            "labels": labels_mod.get_labels(locale),
        }
        if not payload["labels"]:
            payload["_meta"]["warning"] = f"unsupported locale: {locale}"

        cache.set(key, payload, timeout=cache_keys.I18N_TTL_SEC)
        return Response(payload)
