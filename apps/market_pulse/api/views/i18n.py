"""
i18n endpoint (PR-J).

소속: apps/market_pulse/api/views (app 레이어 DRF Views).
역할: i18n/labels.KO_LABELS 한글 매핑 전체를 FE 클라이언트에 응답.
  FE 초기 로드 시 1회 호출 → 카드 라벨/regime/anomaly 명칭 표시.
"""

from __future__ import annotations

from django.core.cache import cache
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_pulse.api import cache as cache_keys
from apps.market_pulse.i18n import labels as labels_mod
from apps.market_pulse.throttles import MarketPulseHourThrottle, MarketPulseUserThrottle


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
