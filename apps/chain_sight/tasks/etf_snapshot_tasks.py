"""
C4 ETF 플로우 원료 스냅샷 태스크 (TH-7c, 결정11=A) — 설계 앵커 §7.

- snapshot_etf_metrics_task: 일간(heat 18:00 ET 이전) — active primary ETF(섹터 SPDR 11종)의
  shares_out·nav·aum 스냅샷을 EtfSnapshot 에 멱등 적립. C4 산식은 미배선(원료만, §2).

공통: macOS fork 안전(Bug #25), retry 관례(max_retries=3, exp backoff), 실패 알림은
REFRESH-ALERT 와 같은 채널(_alert = ERROR 로그 + send_mail best-effort). 명시 beat 등록(#28).
"""

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="chainsight-snapshot-etf-metrics",
    bind=True,
    max_retries=3,
    soft_time_limit=600,
    time_limit=660,
)
def snapshot_etf_metrics_task(self):
    """일간 C4 원료 수집 (§7, heat 직전). active primary ETF shares_out·nav·aum. 멱등."""
    from django import db

    db.connections.close_all()  # macOS fork 안전 (Bug #25)

    from apps.chain_sight.services.etf_snapshot_service import (
        active_primary_etf_symbols,
        snapshot_etf_metrics,
    )
    from apps.chain_sight.tasks.universe_tasks import _alert
    from packages.shared.api_request.providers.fmp.client import FMPClient

    snapshot_date = timezone.now().date()
    symbols = active_primary_etf_symbols()

    if not symbols:
        # 시드 부재 = 이상 (SPDR 11종 시드 확인 필요) → 알림, 재시도 무의미.
        _alert("C4 ETF 스냅샷 — 대상 없음",
               "active primary ThemeEtfMap 0건 — 섹터 SPDR 시드 확인 필요")
        return {"snapshot_date": snapshot_date.isoformat(), "symbols": 0, "created": 0}

    client = FMPClient(api_key=settings.FMP_API_KEY)
    try:
        result = snapshot_etf_metrics(client, symbols, snapshot_date)
    except Exception as exc:  # noqa: BLE001
        _alert("C4 ETF 스냅샷 실패(예외)", f"{type(exc).__name__}: {exc}")
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))

    # 전 심볼 가드 skip(저장 0건) = 이상 응답 → 알림(태스크는 성공 반환, 로그가 정본).
    if result["created"] + result["updated"] == 0:
        _alert("C4 ETF 스냅샷 — 저장 0건",
               f"전 심볼 가드 skip: {result['skipped_symbols']}")

    return {
        "snapshot_date": snapshot_date.isoformat(),
        "symbols": len(symbols),
        "created": result["created"],
        "updated": result["updated"],
        "skipped": result["skipped"],
    }
