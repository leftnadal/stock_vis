"""
Translation Celery task (Phase 1.5 S3) — `mp_generate_translation_daily`.

소속: apps/market_pulse/tasks (app 레이어 Celery task, Brief task 미러).
역할: 평일 NY 17:45 (KST 06:45) — 당일 4 스냅샷 → 1회 Gemini 동기 호출 →
  카드별 감각 유추 JSON → TranslationLog 1행 upsert(같은 날 재실행 시 덮어쓰기).
스케줄: Beat name `mp_generate_translation_daily`, crontab NY 17:45 평일
  (finalize 16:30·concentration/brief 17:15·yahoo 17:35·fred 17:40 뒤 = 카드 데이터 최종화 후).
주의: Bug #8 — Celery에서 async LLM 호출 금지. 공용 동기 plumbing(llm.client) 사용.
  Bug #28 — beat는 setup_marketpulse_beat가 DB 직접 등록 → 배포 시 재실행 필수.
호출자: Celery Beat scheduler만.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone as django_timezone

from apps.market_pulse.llm import translation_prompt as prompt_mod
from apps.market_pulse.llm import translation_safety as safety_mod
from apps.market_pulse.llm.client import DEFAULT_MODEL, generate_with_circuit
from apps.market_pulse.models.translation import TranslationLog

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.translation.mp_generate_translation_daily",
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=180,
    time_limit=240,
)
def mp_generate_translation_daily(self, **kwargs: Any) -> dict[str, Any]:
    today = django_timezone.localdate()
    context = prompt_mod.build_translation_context(today)

    if not prompt_mod.is_sufficient(context):
        # 데이터 부족 — LLM 호출 안 함(비용 절약). 빈 OK 금지 → REFUSED + 사유 로그.
        logger.warning("translation skipped: insufficient snapshot data for %s", today)
        log, _ = TranslationLog.objects.update_or_create(
            date=today,
            model_version=DEFAULT_MODEL,
            defaults={
                "status": TranslationLog.Status.REFUSED,
                "senses": {},
                "prompt_inputs": context,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency_ms": 0,
            },
        )
        return _summary(log, ["insufficient_data"])

    contents: list = []
    contents.extend(prompt_mod.few_shot_messages())
    contents.append(
        {"role": "user", "parts": [{"text": prompt_mod.render_user_prompt(context)}]}
    )

    try:
        raw = generate_with_circuit(
            system_instruction=prompt_mod.SYSTEM_PROMPT, contents=contents
        )
    except Exception as exc:
        countdown = 300 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    result = safety_mod.validate_senses(raw.text)
    if result.issues:
        logger.warning("translation issues %s for %s", result.issues, today)

    log, _ = TranslationLog.objects.update_or_create(
        date=today,
        model_version=DEFAULT_MODEL,
        defaults={
            "status": result.status,
            "senses": result.senses,
            "prompt_inputs": context,
            "prompt_tokens": raw.prompt_tokens,
            "completion_tokens": raw.completion_tokens,
            "latency_ms": raw.latency_ms,
            # cost_usd: Gemini 단가 단일출처 부재 → Brief와 동일하게 null 유지(추후 결정).
        },
    )
    return _summary(log, result.issues)


def _summary(log: TranslationLog, issues: list[str]) -> dict[str, Any]:
    return {
        "date": log.date.isoformat(),
        "model_version": log.model_version,
        "status": log.status,
        "sense_keys": sorted(log.senses.keys()),
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "latency_ms": log.latency_ms,
        "issues": issues,
    }
