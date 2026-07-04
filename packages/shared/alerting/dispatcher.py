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
from packages.shared.alerting.registry import get_alert_renderer

logger = logging.getLogger(__name__)


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
        subs = list(
            AlertSubscription.objects.filter(
                source_app=event.source_app,
                event_type=event.event_type,
                enabled=True,
            )
        )
        for sub in subs:
            subject, text_body, html_body = renderer(event.payload)
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
        log.error = ""
        log.save(update_fields=["subscription", "status", "sent_at", "error"])
    except Exception as exc:
        log.status = AlertDispatchLog.Status.FAILED
        log.error = f"{type(exc).__name__}: {exc}"
        log.save(update_fields=["status", "error"])
        logger.warning("alert dispatch failed[%s]: %s", event.dedup_key, log.error)
        raise
