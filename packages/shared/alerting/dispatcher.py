"""디스패처 + 정책(dedup) — 이벤트 1건을 구독자에게 전달.

dedup: dedup_key로 get_or_create. 이미 sent면 무발송·무행(15분 재트리거·당일 flip 왕복
대응 — transitioned가 전일 대비라 전환일 하루 종일 매 사이클 True). 신규 또는 기존 failed면
발송 시도 → 15분 주기가 자연 재시도. 발송 예외는 failed+error 기록 후 전파(트리거는 별도
fire-and-forget task라 regime 본연 무손상).
"""
from __future__ import annotations

import logging

from django.utils import timezone

from packages.shared.alerting.delivery.base import get_provider
from packages.shared.alerting.events import AlertEvent
from packages.shared.alerting.models import AlertDispatchLog, AlertSubscription
from packages.shared.alerting.registry import get_alert_fallback, get_alert_renderer

logger = logging.getLogger(__name__)

# MP2-ALERTS S1: 렌더 폴백 사유 접두 — status=SENT + error 이 접두 = "발송됐으나 최소본문 폴백".
#   status=FAILED(발송 실패)와 로그에서 구분(마이그레이션 0 — 기존 error 필드 재사용).
RENDER_FALLBACK_PREFIX = "RENDER_FALLBACK: "


def dispatch(event: AlertEvent) -> None:
    log, created = AlertDispatchLog.objects.get_or_create(
        dedup_key=event.dedup_key,
        defaults={
            "source_app": event.source_app,
            "event_type": event.event_type,
            "payload": event.payload,
            "status": AlertDispatchLog.Status.FAILED,
        },
    )
    if not created and log.status == AlertDispatchLog.Status.SENT:
        return  # 이미 발송 완료 — 재발송·행 추가 억제

    try:
        renderer = get_alert_renderer(event.source_app, event.event_type)
        # MP2-ALERTS S1: 본문 1회 렌더(구독 무관 동일). 렌더 예외 → 폴백 렌더러(있으면)로 대체해
        #   발송 자체는 실패하지 않는다. 폴백 사유는 error 필드(RENDER_FALLBACK_PREFIX)에 기록.
        fallback_note = ""
        try:
            subject, text_body, html_body = renderer(event.payload)
        except Exception as render_exc:
            fallback = get_alert_fallback(event.source_app, event.event_type)
            if fallback is None:
                raise
            subject, text_body, html_body = fallback(event.payload)
            fallback_note = f"{RENDER_FALLBACK_PREFIX}{type(render_exc).__name__}: {render_exc}"
            logger.warning(
                "alert render fallback[%s]: %s", event.dedup_key, fallback_note
            )
        subs = list(
            AlertSubscription.objects.filter(
                source_app=event.source_app,
                event_type=event.event_type,
                enabled=True,
            )
        )
        for sub in subs:
            get_provider(sub.channel).deliver(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                destination=sub.destination,
            )
        # 구독 0/비활성이어도 발송 시도가 예외 없이 끝나면 sent(억제 정상, 에러 아님).
        log.subscription = subs[0] if len(subs) == 1 else None
        log.status = AlertDispatchLog.Status.SENT
        log.sent_at = timezone.now()
        log.error = fallback_note  # 폴백 발생 시 사유 기록, 아니면 ""(전건 정상)
        log.save(update_fields=["subscription", "status", "sent_at", "error"])
    except Exception as exc:
        log.status = AlertDispatchLog.Status.FAILED
        log.error = f"{type(exc).__name__}: {exc}"
        log.save(update_fields=["status", "error"])
        logger.warning("alert dispatch failed[%s]: %s", event.dedup_key, log.error)
        raise
