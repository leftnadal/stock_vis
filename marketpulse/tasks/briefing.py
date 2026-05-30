"""Market Pulse v2 — Briefing Celery task (PR-E)."""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone as django_timezone

from marketpulse.briefing import client as client_mod
from marketpulse.briefing import prompt as prompt_mod
from marketpulse.briefing import safety as safety_mod
from marketpulse.briefing.prompt import DISCLAIMER
from marketpulse.models.briefing import BriefingLog

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="marketpulse.tasks.briefing.mp_generate_brief_daily",
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=180,
    time_limit=240,
)
def mp_generate_brief_daily(self, **kwargs: Any) -> dict[str, Any]:
    today = django_timezone.localdate()
    ctx = prompt_mod.build_context_from_snapshots(today)

    if ctx.regime is None or ctx.breadth_advance is None:
        log, _ = BriefingLog.objects.update_or_create(
            date=today,
            model_version=client_mod.DEFAULT_MODEL,
            defaults={
                "status": BriefingLog.Status.INSUFFICIENT_DATA,
                "headline": "데이터 수집 부족 — 브리핑 생성 보류",
                "body": "오늘 자 Regime / Breadth 스냅샷이 부족하여 브리핑을 생성하지 않았습니다. "
                + DISCLAIMER,
                "prompt_inputs": ctx.as_dict(),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency_ms": 0,
            },
        )
        return _summary(log)

    try:
        raw = client_mod.generate(ctx)
    except Exception as exc:
        countdown = 300 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    safety = safety_mod.validate(raw.text)
    log, _ = BriefingLog.objects.update_or_create(
        date=today,
        model_version=client_mod.DEFAULT_MODEL,
        defaults={
            "status": safety.status,
            "headline": safety.headline,
            "body": safety.content,
            "prompt_inputs": ctx.as_dict(),
            "prompt_tokens": raw.prompt_tokens,
            "completion_tokens": raw.completion_tokens,
            "latency_ms": raw.latency_ms,
        },
    )
    return _summary(log)


def _summary(log: BriefingLog) -> dict[str, Any]:
    return {
        "date": log.date.isoformat(),
        "model_version": log.model_version,
        "status": log.status,
        "headline": log.headline,
        "content_preview": log.body[:200],
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "latency_ms": log.latency_ms,
    }
