"""
Heat 일배치 태스크 (TH-5) — 설계 앵커 v1.2.2 §7.

- compute_theme_heat_task: 일간 ET 18:00 — E2 증분 → C1~C8 → Heat upsert.
- collect_theme_filings_task: 일간 heat 직전 — C2b 424B5 일창 수집 + IPO(진성 필터).

공통: 성분/단계별 try/except 실패 격리, macOS fork 안전(Bug #25), retry 관례
(max_retries=3, countdown=300*(retries+1)). 명시 beat 등록(Bug #28) = register_chainsight_beats.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="chainsight-theme-heat-daily",
    bind=True,
    max_retries=3,
    soft_time_limit=1800,
    time_limit=1860,
)
def compute_theme_heat_task(self):
    """일간 Heat 배치 (§7). E2 내부자 증분(best-effort) → compute_theme_heat upsert."""
    from django import db

    db.connections.close_all()  # macOS fork 안전 (Bug #25)

    from apps.chain_sight.services.heat_beat import compute_theme_heat

    as_of = timezone.now().date()

    # E2 내부자 증분 (best-effort — 실패해도 heat 계산은 진행)
    try:
        from apps.chain_sight.services.insider_service import collect_latest
        from packages.shared.api_request.providers.fmp.client import FMPClient

        e2 = collect_latest(FMPClient(api_key=settings.FMP_API_KEY))
        logger.info("heat beat E2 증분: %s", e2)
    except Exception as e:  # noqa: BLE001 — 증분 실패 격리
        logger.warning("heat beat E2 증분 실패(격리): %s", e)

    try:
        results = compute_theme_heat(as_of)
    except Exception as exc:  # noqa: BLE001
        logger.error("compute_theme_heat_task 실패: %s", exc)
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))

    stored = sum(1 for r in results if r["stored"])
    return {"as_of": as_of.isoformat(), "sectors": len(results), "stored": stored}


@shared_task(
    name="chainsight-collect-theme-filings",
    bind=True,
    max_retries=3,
    soft_time_limit=1800,
    time_limit=1860,
)
def collect_theme_filings_task(self, days: int = 3):
    """일간 C2b 수집 (§7, heat 직전). 최근 days 일 424B5 일창 + IPO(진성 필터). 멱등."""
    from django import db

    db.connections.close_all()

    from apps.chain_sight.services.filing_service import (
        collect_424b5_range,
        collect_ipos_range,
    )
    from packages.shared.api_request.providers.fmp.client import FMPClient

    to_date = timezone.now().date()
    from_date = to_date - timedelta(days=days - 1)
    client = FMPClient(api_key=settings.FMP_API_KEY)

    try:
        b5 = collect_424b5_range(client, from_date, to_date, log_fn=logger.info)
        ipo = collect_ipos_range(client, from_date, to_date)
    except Exception as exc:  # noqa: BLE001
        logger.error("collect_theme_filings_task 실패: %s", exc)
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))

    logger.info("C2b 수집 완료 %s~%s: 424B5=%s IPO=%s", from_date, to_date, b5, ipo)
    return {"from": from_date.isoformat(), "to": to_date.isoformat(),
            "b5_created": b5["created"], "ipo_created": ipo["created"]}
