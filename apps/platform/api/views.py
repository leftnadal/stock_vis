"""apps/platform telemetry 수신 API (D-P2-S2-PLATFORM, P2-IMPRESSION-BUILD-S2).

impression/click 이벤트 배치(sendBeacon)를 shared ImpressionLog 에 기록한다.
경계 #43: IssuanceLog(bake-time)는 무접촉 — serve-time ImpressionLog 에만 write.
"""
from __future__ import annotations

from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from packages.shared.stocks.models import ImpressionLog

# 배치 상한 (도그푸딩 튜닝 대상 상수 — STRIP-FOLD-TUNE 패턴). 초과 시 413.
MAX_IMPRESSION_BATCH = 100

_VALID_SURFACES = {c[0] for c in ImpressionLog.SURFACE_CHOICES}
_VALID_EVENTS = {ImpressionLog.EVENT_IMPRESSION, ImpressionLog.EVENT_CLICK}


def _clean_item(item):
    """유효 이벤트면 정규화 dict, 아니면 None(거부)."""
    if not isinstance(item, dict):
        return None
    surface = item.get("surface")
    object_ref = item.get("object_ref")
    event_type = item.get("event_type")
    session_id = item.get("session_id")
    if surface not in _VALID_SURFACES:
        return None
    if event_type not in _VALID_EVENTS:
        return None
    if not object_ref or not isinstance(object_ref, str):
        return None
    if not session_id or not isinstance(session_id, str):
        return None
    return {
        "surface": surface,
        "object_ref": object_ref[:128],
        "event_type": event_type,
        "session_id": session_id[:64],
    }


def _record(user_id, ev, now):
    """단일 유효 이벤트 기록. impression=partial-unique upsert(seen_count 원자 증가·
    first_seen_at 최초 고정), click=무조건 append."""
    if ev["event_type"] == ImpressionLog.EVENT_IMPRESSION:
        key = dict(
            user_id=user_id,
            surface=ev["surface"],
            object_ref=ev["object_ref"],
            event_type=ImpressionLog.EVENT_IMPRESSION,
        )
        updated = ImpressionLog.objects.filter(**key).update(
            seen_count=F("seen_count") + 1
        )
        if not updated:
            try:
                ImpressionLog.objects.create(
                    seen_count=1,
                    first_seen_at=now,
                    session_id=ev["session_id"],
                    **key,
                )
            except IntegrityError:
                # 동시 생성 레이스(partial unique) → 증가로 수렴
                ImpressionLog.objects.filter(**key).update(
                    seen_count=F("seen_count") + 1
                )
    else:  # click → 유니크 없음, 무조건 append
        ImpressionLog.objects.create(
            user_id=user_id,
            surface=ev["surface"],
            object_ref=ev["object_ref"],
            event_type=ImpressionLog.EVENT_CLICK,
            seen_count=0,
            first_seen_at=now,
            session_id=ev["session_id"],
        )


class ImpressionIngestView(APIView):
    """POST /api/v1/telemetry/impressions — impression/click 배치 수신.

    payload = 이벤트 배열 `[{surface, object_ref, event_type, session_id}, ...]`(sendBeacon 계약).
    - impression: (user_id, surface, object_ref) partial-unique upsert → seen_count += 1,
      first_seen_at 최초 고정(이후 불변). click: 무조건 append.
    - 유효 항목만 처리 + 거부 건수 응답(배치 유실 최소화). 배열 상한 MAX_IMPRESSION_BATCH.
    - 인증 필수(익명 거부). user_id = request.user.id (모델의 nullable user_id 는 예약, 미사용).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response({"detail": "payload must be a JSON array"}, status=400)
        if len(data) > MAX_IMPRESSION_BATCH:
            return Response(
                {"detail": f"batch too large (> {MAX_IMPRESSION_BATCH})"},
                status=413,
            )
        user_id = request.user.id
        now = timezone.now()
        received = 0
        rejected = 0
        for item in data:
            ev = _clean_item(item)
            if ev is None:
                rejected += 1
                continue
            _record(user_id, ev, now)
            received += 1
        return Response({"received": received, "rejected": rejected})
