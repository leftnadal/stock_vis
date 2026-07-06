"""MP2-ALERTS 트리거 태스크 — regime 전환 → 표준 봉투 emit(fire-and-forget).

regime task가 `.delay()`로 enqueue만 하고 즉시 반환한다 → 알림 파이프라인 실패가
regime 본연을 깨지 않는다(격리). 입력은 트리거 시점 decision 값만 받는다(transitioned는
transient — 스냅샷 미저장이라 재조회 금지).
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def fire_regime_transition_alert(date: str, from_regime: str, to_regime: str) -> None:
    from packages.shared.alerting.events import AlertEvent, emit

    emit(
        AlertEvent(
            source_app="market_pulse",
            event_type="regime_transition",
            occurred_at=timezone.now(),
            dedup_key=f"regime_transition:{date}:{from_regime}:{to_regime}",
            payload={
                "date": date,
                "from_regime": from_regime,
                "to_regime": to_regime,
            },
        )
    )
