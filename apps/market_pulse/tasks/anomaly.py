"""
Anomaly Celery task (PR-D) — `mp_detect_anomaly_5min`.

소속: apps/market_pulse/tasks (app 레이어 Celery task).
역할: 평일 09:30~16:30 매 5분 — anomaly.engine.build_context + load_rules + evaluate +
  select_mode + fallback.build + news_pairing.find_pair → AnomalySignalLog 적재.
스케줄: Beat name `mp_detect_anomaly_5min`, crontab `*/5` 평일 시장 시간대 한정.
주의: max_retries=3, exponential backoff(`60 * 2**retries`). soft_time_limit=120s.
호출자: Celery Beat scheduler만(코드 직접 호출 없음).
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone as django_timezone

from apps.market_pulse.anomaly import engine as engine_mod
from apps.market_pulse.anomaly import fallback as fallback_mod
from apps.market_pulse.anomaly import news_pairing as pairing_mod
from apps.market_pulse.models.anomaly import AnomalySignalLog

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.anomaly.mp_detect_anomaly_5min",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    time_limit=180,
)
def mp_detect_anomaly_5min(self, **kwargs: Any) -> dict[str, Any]:
    try:
        ctx = engine_mod.build_context()
        rules_data = engine_mod.load_rules()
        fired = engine_mod.evaluate(ctx, rules=rules_data)
        mode = engine_mod.select_mode(fired)
        slots = fallback_mod.build(fired=fired, ctx=ctx, mode=mode)
        paired_news = pairing_mod.find_pair(fired, ctx)

        triggered_at = django_timezone.now()
        log_pks = []
        for f in fired:
            log = AnomalySignalLog.objects.create(
                rule_id=f.rule_id,
                triggered_at=triggered_at,
                inputs={
                    "top10_weight": ctx.top10_weight,
                    "vix_change_pct": ctx.vix_change_pct,
                    "max_abs_sector_z": ctx.max_abs_sector_z,
                    "cross_dispersion": ctx.cross_dispersion,
                    "sector_extreme_symbol": ctx.sector_extreme_symbol,
                    "sector_extreme_z": ctx.sector_extreme_z,
                    "sources": ctx.sources,
                    "fetched_at": ctx.fetched_at,
                    "rule_actual": f.actual,
                },
                threshold=f.threshold,
                paired_news=paired_news,
                mode=mode,
                headline=f"{f.name} 발동",
                body=slots.overview,
            )
            log_pks.append(log.pk)
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    return {
        "mode": mode,
        "fired_rules": [{"id": f.rule_id, "actual": f.actual} for f in fired],
        "slots": {
            "overview": slots.overview,
            "sector_highlight": slots.sector_highlight,
            "portfolio_action": slots.portfolio_action,
        },
        "paired_news_id": paired_news.pk if paired_news else None,
        "log_pks": log_pks,
        "context": {
            "top10_weight": ctx.top10_weight,
            "vix_change_pct": ctx.vix_change_pct,
            "cross_dispersion": ctx.cross_dispersion,
            "max_abs_sector_z": ctx.max_abs_sector_z,
            "sector_extreme_symbol": ctx.sector_extreme_symbol,
        },
        "sources": ctx.sources,
    }
