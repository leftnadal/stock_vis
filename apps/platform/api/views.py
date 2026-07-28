"""apps/platform telemetry 수신 API (D-P2-S2-PLATFORM, P2-IMPRESSION-BUILD-S2).

impression/click 이벤트 배치(sendBeacon)를 shared ImpressionLog 에 기록한다.
경계 #43: IssuanceLog(bake-time)는 무접촉 — serve-time ImpressionLog 에만 write.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from packages.shared.stocks.models import ImpressionLog, IssuanceLog

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


# ── P2-COVERAGE-C1-API: 발급(IssuanceLog) 대비 노출(ImpressionLog) 커버리지 조회 ──
#
# 읽기 전용 compute-on-read. 경계 #43: IssuanceLog·ImpressionLog **읽기만**(스키마 무변경).
# 의존 방향 platform → shared (읽기 조인). 조인 키 = object_ref 문자열 동치.
#   IssuanceLog grain(stock, signal_date, signal_tag) → `SYMBOL:YYYY-MM-DD:TAG`
#   ↔ FE recoObjectRef(ticker, tradingDate, signalTag) 단일 출처와 바이트 정합(실측 2026-07-24).
#   (Stock PK=symbol 이므로 iss.stock_id 가 곧 심볼 문자열 — select_related 불요.)

# 창 상수 (요청 window_days 파싱 기준)
DEFAULT_COVERAGE_WINDOW_DAYS = 7
MAX_COVERAGE_WINDOW_DAYS = 90

# 응답 미노출 리스트 상한 (임시 상수 — C-2 튜닝 대상)
UNEXPOSED_RESPONSE_LIMIT = 50

# 커버리지 유기 표면 = 발급 grain object_ref 를 쓰는 표면만(현재 dashboard_eod).
# news_chip 은 object_ref=URL(발급 grain 아님) → 커버리지 조인 대상 아님.
# 향후 표면 추가 시 grain 정합 확인 후 이 화이트리스트에 편입(C-2). surfaces_included 의 단일 근거.
COVERAGE_SURFACES = (ImpressionLog.SURFACE_DASHBOARD_EOD,)

# 상세 페이지 자기노출 표면 — 유기 지표 오염 격리(D-P2-COVERAGE-SURFACE)로 exposed 집계서 제외.
# 아직 ImpressionLog.SURFACE_CHOICES 미등재(C1-FE 가 발신 예정) → 방어적 제외.
COVERAGE_DETAIL_SURFACE = "coverage_detail"


class CoverageView(APIView):
    """GET /api/v1/telemetry/coverage — 발급 대비 유기 노출 커버리지(요청 사용자 스코프).

    - IssuanceLog(발급, user-agnostic day-1) 를 window_days(발급 signal_date 기준 창) 로 집계 = issued.
    - 그 중 요청 사용자가 유기 표면(COVERAGE_SURFACES, coverage_detail 제외)에서 impression 한 건 = exposed.
    - 미노출(issued − exposed) 리스트는 signal_date desc, 상한 UNEXPOSED_RESPONSE_LIMIT.
    - 사용자 impression 이나 in-window 발급 grain 에 매칭 안 되는 건 = meta.join_misses(침묵 유실 금지).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw = request.query_params.get("window_days")
        window_days = DEFAULT_COVERAGE_WINDOW_DAYS
        if raw is not None:
            try:
                window_days = int(raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "window_days must be an integer"}, status=400
                )
            if window_days < 1:
                return Response(
                    {"detail": "window_days must be >= 1"}, status=400
                )
            window_days = min(window_days, MAX_COVERAGE_WINDOW_DAYS)

        to_date = timezone.localdate()
        from_date = to_date - timedelta(days=window_days)

        # 발급 grain → object_ref (user-agnostic). unique_together 보장으로 ref 충돌 없음.
        issued_map = {
            f"{iss.stock_id}:{iss.signal_date.isoformat()}:{iss.signal_tag}": iss
            for iss in IssuanceLog.objects.filter(
                signal_date__gte=from_date, signal_date__lte=to_date
            )
        }
        issued_refs = set(issued_map)
        issued = len(issued_refs)

        # 요청 사용자의 유기 노출 refs (coverage_detail 방어적 제외).
        imp_refs = set(
            ImpressionLog.objects.filter(
                user_id=request.user.id,
                event_type=ImpressionLog.EVENT_IMPRESSION,
                surface__in=COVERAGE_SURFACES,
            )
            .exclude(surface=COVERAGE_DETAIL_SURFACE)
            .values_list("object_ref", flat=True)
        )

        exposed_refs = issued_refs & imp_refs
        exposed = len(exposed_refs)
        unexposed_refs = issued_refs - imp_refs
        unexposed_count = len(unexposed_refs)
        # in-window 발급에 귀속 안 되는 사용자 노출(창밖 발급·grain 불일치 등) — exposed 에 세지 않고 보고만.
        join_misses = len(imp_refs - issued_refs)

        unexposed_items = sorted(
            (issued_map[r] for r in unexposed_refs),
            key=lambda i: i.signal_date,
            reverse=True,
        )[:UNEXPOSED_RESPONSE_LIMIT]
        unexposed = [
            {
                "object_ref": f"{i.stock_id}:{i.signal_date.isoformat()}:{i.signal_tag}",
                "ticker": i.stock_id,
                "signal_date": i.signal_date.isoformat(),
                "signal_tag": i.signal_tag,
                "days_since_issue": (to_date - i.signal_date).days,
            }
            for i in unexposed_items
        ]

        exposure_rate = round(exposed / issued, 4) if issued else 0.0

        return Response(
            {
                "window": {
                    "days": window_days,
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                },
                "summary": {
                    "issued": issued,
                    "exposed": exposed,
                    "exposure_rate": exposure_rate,
                    "unexposed_count": unexposed_count,
                },
                "unexposed": unexposed,
                "meta": {
                    "surfaces_included": list(COVERAGE_SURFACES),
                    "generated_at": timezone.now().isoformat(),
                    "join_misses": join_misses,
                },
            }
        )
