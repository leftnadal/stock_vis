"""Market Pulse v2 — Regime Classifier task (PR-C)."""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone as django_timezone

from marketpulse.models.regime import RegimeSnapshot
from marketpulse.regime import classifier as classifier_mod
from marketpulse.regime import coverage as coverage_mod
from marketpulse.regime import inputs as inputs_mod

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="marketpulse.tasks.regime.mp_calc_regime_15min",
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
