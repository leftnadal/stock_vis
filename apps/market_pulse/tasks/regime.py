"""
intraday Regime Classifier task (PR-C) — `mp_calc_regime_15min`.

소속: apps/market_pulse/tasks (app 레이어 Celery task).
역할: 매 15분 — regime.inputs.load_inputs(14 매크로지표) + classifier.load_rules +
  classify_inputs + apply_hysteresis → RegimeSnapshot upsert(date 단위).
스케줄: Beat name `mp_calc_regime_15min`, crontab `*/15`.
주의: 이 task는 **intraday 5단계 regime** 전용. packages/shared 의 EOD 3단계
  레짐(DynamicRegimeCalculator)과 별개. 입력·알고리즘·소비처 모두 다름.
호출자: Celery Beat scheduler만(코드 직접 호출 없음).
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone as django_timezone

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime import classifier as classifier_mod
from apps.market_pulse.regime import coverage as coverage_mod
from apps.market_pulse.regime import inputs as inputs_mod

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.market_pulse.tasks.regime.mp_calc_regime_15min",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
    time_limit=180,
)
def mp_calc_regime_15min(self, **kwargs: Any) -> dict[str, Any]:
    try:
        inputs = inputs_mod.load_inputs()
        rules = classifier_mod.load_rules()
        coverage = coverage_mod.evaluate(inputs, rules=rules)
        today = django_timezone.localdate()
        previous = (
            RegimeSnapshot.objects.filter(date__lt=today)
            .order_by("-date", "-snapshot_time")
            .first()
        )

        if coverage.status == RegimeSnapshot.Status.INSUFFICIENT_DATA:
            candidate, fired = classifier_mod.classify_inputs(inputs, rules=rules)
            decision = classifier_mod.HysteresisDecision(
                final_regime=previous.regime if previous else candidate,
                previous_regime=previous.regime if previous else "",
                streak=int(previous.hysteresis_streak or 1) if previous else 1,
                transitioned=False,
            )
            status = RegimeSnapshot.Status.INSUFFICIENT_DATA
        else:
            candidate, fired = classifier_mod.classify_inputs(inputs, rules=rules)
            decision = classifier_mod.apply_hysteresis(
                candidate_regime=candidate,
                previous_snapshot=previous,
                rules=rules,
            )
            status = RegimeSnapshot.Status.OK

        headline = classifier_mod.build_headline(decision.final_regime, fired)

        snapshot, _ = RegimeSnapshot.objects.update_or_create(
            date=today,
            defaults={
                "snapshot_time": django_timezone.now(),
                "regime": decision.final_regime,
                "status": status,
                "inputs": inputs.as_dict(),
                "coverage": coverage.ratio,
                "fired_rules": fired,
                "previous_regime": decision.previous_regime,
                "hysteresis_streak": decision.streak,
                "headline": headline[:300],
                "summary": "",
                "is_finalized": False,
                "finalized_at": None,
            },
        )
    except Exception as exc:
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    # MP2-ALERTS 훅(try/except 밖 — regime 본연 무손상): 전환 시 fire-and-forget 알림.
    # transitioned은 transient(스냅샷 미저장) → decision 값만 넘기고 재조회 금지.
    # enqueue 실패조차 regime task를 깨지 않도록 방어(로그만).
    if decision.transitioned:
        try:
            from apps.market_pulse.tasks.alerts import fire_regime_transition_alert

            fire_regime_transition_alert.delay(
                date=snapshot.date.isoformat(),
                from_regime=decision.previous_regime,
                to_regime=decision.final_regime,
            )
        except Exception:  # pragma: no cover - broker 장애 방어
            logger.exception("regime transition alert enqueue 실패(무시)")

    return {
        "date": snapshot.date.isoformat(),
        "regime": snapshot.regime,
        "status": snapshot.status,
        "coverage": round(snapshot.coverage, 3),
        "fired_rules": snapshot.fired_rules,
        "previous_regime": snapshot.previous_regime,
        "hysteresis_streak": snapshot.hysteresis_streak,
        "transitioned": decision.transitioned,
        "missing_inputs": coverage.missing,
        "headline": snapshot.headline,
    }
