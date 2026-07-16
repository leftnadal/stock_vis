"""apps/platform telemetry 수신 API (D-P2-S2-PLATFORM, P2-IMPRESSION-BUILD-S2).

impression/click 이벤트 배치(sendBeacon)를 shared ImpressionLog 에 기록한다.
경계 #43: IssuanceLog(bake-time)는 무접촉 — serve-time ImpressionLog 에만 write.
"""
from __future__ import annotations

import logging

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from packages.shared.stocks.models import ImpressionLog

logger = logging.getLogger(__name__)

# 배치 상한 (도그푸딩 튜닝 대상 상수 — STRIP-FOLD-TUNE 패턴). 초과 시 413.
MAX_IMPRESSION_BATCH = 100

# rejected 사유 코드 (응답 봉투 rejected_reasons 키)
REJECT_INVALID = "invalid"      # _clean_item 검증 실패(형식/허용값)
REJECT_DB_ERROR = "db_error"    # 항목 단위 구조적 DB 오류(IntegrityError/DataError 등)

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
                # 레이스 IntegrityError를 중첩 savepoint로 격리 →
                # 외부 per-item atomic(트랜잭션)을 오염시키지 않고 아래 복구 update 실행 가능.
                with transaction.atomic():
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
    - **per-item 격리(PLATFORM-INGEST-DB-ISOLATE)**: 각 항목을 개별 savepoint(transaction.atomic)로
      감싸 구조적 DB 오류(IntegrityError/DataError 등)가 **항목 단위로만** 실패하도록 한다.
      정상 항목은 전량 수신되고, 실패 항목만 rejected(db_error)로 집계 — 배치 전체 500 없음.
    - 응답 봉투 = {received(=accepted), rejected, rejected_reasons{code: count}}.
      배치가 비거나 전 항목 실패여도 500이 아닌 정상 2xx로 rejected 전량 보고.
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
        rejected_reasons: dict[str, int] = {}
        for item in data:
            ev = _clean_item(item)
            if ev is None:
                rejected_reasons[REJECT_INVALID] = (
                    rejected_reasons.get(REJECT_INVALID, 0) + 1
                )
                continue
            try:
                # per-item savepoint — 이 항목의 구조적 DB 오류가 다른 항목·배치 전체를
                # 무너뜨리지 않도록 격리(rollback 범위 = 이 항목만).
                with transaction.atomic():
                    _record(user_id, ev, now)
            except DatabaseError:
                # IntegrityError/DataError 등 구조적 DB 오류 → 항목 단위 거부, 배치 유지.
                rejected_reasons[REJECT_DB_ERROR] = (
                    rejected_reasons.get(REJECT_DB_ERROR, 0) + 1
                )
                logger.warning(
                    "impression ingest 항목 DB 오류로 거부 (surface=%s, event_type=%s)",
                    ev["surface"],
                    ev["event_type"],
                    exc_info=True,
                )
                continue
            received += 1
        rejected = sum(rejected_reasons.values())
        return Response(
            {
                "received": received,
                "rejected": rejected,
                "rejected_reasons": rejected_reasons,
            }
        )
