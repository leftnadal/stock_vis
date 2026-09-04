"""Data Eligibility Gate for Math Lab research.

The gate answers a narrow question before a material data input is used:
"Is this data view eligible for the declared research use?"

It deliberately does not decide whether a dataset is *good*, whether a model is
valid, or whether a claim is true. Those remain methodology/evaluation concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Tuple


class IntendedUse(str, Enum):
    EXPLORATORY = "exploratory"
    CONFIRMATORY = "confirmatory"
    REPLICATION = "replication"


class Eligibility(str, Enum):
    CONFIRMATORY_SAFE = "confirmatory_safe"
    EXPLORATORY_ONLY = "exploratory_only"
    PROHIBITED = "prohibited_for_declared_use"


class AvailabilityConfidence(str, Enum):
    EXACT = "exact"
    RECONSTRUCTED = "reconstructed"
    PROXY = "proxy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DataViewContract:
    data_view_id: str
    source_system: str
    intended_use: IntendedUse
    availability_confidence: AvailabilityConfidence
    point_in_time_reconstructable: bool
    content_fingerprint: str | None
    extraction_version: str | None
    universe_version: str | None = None
    entity_resolution_version: str | None = None
    revision_lineage_available: bool = False
    future_information_known: bool = False
    known_contamination: bool = False
    notes: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EligibilityDecision:
    data_view_id: str
    eligibility: Eligibility
    reasons: Tuple[str, ...]
    missing_requirements: Tuple[str, ...]

    @property
    def allowed(self) -> bool:
        return self.eligibility is not Eligibility.PROHIBITED


def _missing_for_confirmation(view: DataViewContract) -> list[str]:
    missing: list[str] = []
    if not view.point_in_time_reconstructable:
        missing.append("point_in_time_reconstructability")
    if view.availability_confidence in {
        AvailabilityConfidence.PROXY,
        AvailabilityConfidence.UNKNOWN,
    }:
        missing.append("sufficient_availability_confidence")
    if not view.content_fingerprint:
        missing.append("content_fingerprint")
    if not view.extraction_version:
        missing.append("extraction_version")
    return missing


def evaluate_data_view(view: DataViewContract) -> EligibilityDecision:
    """Return a deterministic eligibility decision for one declared data view.

    Hard contamination always prohibits the declared use. A clean exploratory
    view may be used for exploration even when point-in-time provenance is weak.
    Confirmation/replication require reconstructable timing, adequate availability
    confidence, a stable content fingerprint, and a versioned extraction path.
    """

    reasons: list[str] = []

    if view.future_information_known:
        return EligibilityDecision(
            view.data_view_id,
            Eligibility.PROHIBITED,
            ("known_future_information",),
            (),
        )

    if view.known_contamination:
        return EligibilityDecision(
            view.data_view_id,
            Eligibility.PROHIBITED,
            ("known_contamination",),
            (),
        )

    missing = _missing_for_confirmation(view)

    if view.intended_use is IntendedUse.EXPLORATORY:
        if missing:
            reasons.append("usable_for_exploration_but_not_confirmation")
            return EligibilityDecision(
                view.data_view_id,
                Eligibility.EXPLORATORY_ONLY,
                tuple(reasons),
                tuple(missing),
            )
        return EligibilityDecision(
            view.data_view_id,
            Eligibility.CONFIRMATORY_SAFE,
            ("meets_current_minimum_data_contract",),
            (),
        )

    if missing:
        reasons.append("declared_use_requires_stronger_data_contract")
        return EligibilityDecision(
            view.data_view_id,
            Eligibility.PROHIBITED,
            tuple(reasons),
            tuple(missing),
        )

    return EligibilityDecision(
        view.data_view_id,
        Eligibility.CONFIRMATORY_SAFE,
        ("meets_current_minimum_data_contract",),
        (),
    )


def evaluate_many(views: Iterable[DataViewContract]) -> tuple[EligibilityDecision, ...]:
    return tuple(evaluate_data_view(view) for view in views)
