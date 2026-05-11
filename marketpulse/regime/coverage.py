"""Market Pulse v2 — Coverage Gate (PR-C)."""
from __future__ import annotations

from dataclasses import dataclass

from marketpulse.models.regime import RegimeSnapshot
from marketpulse.regime.classifier import load_rules
from marketpulse.regime.inputs import RegimeInputs


@dataclass(frozen=True)
class CoverageEvaluation:
    ratio: float
    status: str
    missing: list[str]
    threshold: float


def evaluate(inputs: RegimeInputs, *, rules: dict | None = None) -> CoverageEvaluation:
    rules = rules or load_rules()
    threshold = float(rules.get('coverage', {}).get('min_ratio', 0.6))
    ratio = inputs.coverage_ratio()
    status = (
        RegimeSnapshot.Status.INSUFFICIENT_DATA
        if ratio < threshold
        else RegimeSnapshot.Status.OK
    )
    return CoverageEvaluation(ratio=ratio, status=status, missing=inputs.missing_keys(), threshold=threshold)
