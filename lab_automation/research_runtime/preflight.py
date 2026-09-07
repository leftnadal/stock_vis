"""Research-specific experiment integrity checks.

These checks detect known provenance failures such as evaluator leakage,
independence violations, and protected holdout contamination. They are runtime
integrity checks, not substitutes for Research Lab Evaluation Methodology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from lab_automation.research_runtime.contracts import (
    ExposureProfile,
    StageProfile,
    WorkloadProfile,
)


@dataclass(frozen=True)
class ResearchIntegrityFinding:
    code: str
    status: str
    message: str


def check_expected_answer_leakage(
    workload: WorkloadProfile,
    exposure: ExposureProfile,
) -> ResearchIntegrityFinding:
    protected = set(workload.protected_expectation_refs)
    leaked = sorted(protected.intersection(exposure.all_refs()))
    if leaked:
        return ResearchIntegrityFinding(
            code="expected_answer_leakage",
            status="FAIL",
            message=f"protected expectation material was exposed: {leaked}",
        )
    return ResearchIntegrityFinding(
        code="expected_answer_leakage",
        status="NO_KNOWN_LEAK_DETECTED",
        message="no protected expectation reference is present in declared exposure",
    )


def check_stage_independence(
    stage: StageProfile,
    exposures: Mapping[str, ExposureProfile],
) -> ResearchIntegrityFinding:
    if stage.independence_intent != "independent":
        return ResearchIntegrityFinding(
            code="stage_independence",
            status="NOT_APPLICABLE",
            message="stage does not declare independent execution",
        )

    planned = set(stage.planned_run_ids)
    violations: list[str] = []
    for run_id in planned:
        exposure = exposures.get(run_id)
        if exposure is None:
            continue
        seen_peers = planned.intersection(exposure.prior_run_refs)
        seen_peers.discard(run_id)
        if seen_peers:
            violations.append(f"{run_id} saw {sorted(seen_peers)}")

    if violations:
        return ResearchIntegrityFinding(
            code="stage_independence",
            status="FAIL",
            message="; ".join(violations),
        )
    return ResearchIntegrityFinding(
        code="stage_independence",
        status="PASS",
        message="no declared peer-run exposure was found",
    )


def check_holdout_contamination(
    workload: WorkloadProfile,
    exposure: ExposureProfile,
    *,
    contaminated_refs: Iterable[str],
) -> ResearchIntegrityFinding:
    if workload.evaluation_partition != "protected_holdout":
        return ResearchIntegrityFinding(
            code="holdout_contamination",
            status="NOT_APPLICABLE",
            message="workload is not a protected holdout",
        )
    contaminated = set(contaminated_refs).intersection(exposure.all_refs())
    if contaminated:
        return ResearchIntegrityFinding(
            code="holdout_contamination",
            status="FAIL",
            message=f"known contaminated material exposed: {sorted(contaminated)}",
        )
    return ResearchIntegrityFinding(
        code="holdout_contamination",
        status="NO_KNOWN_CONTAMINATION",
        message="no known contaminated reference is present in declared exposure",
    )


def check_stage_completion(
    stage: StageProfile,
    completed_run_ids: Iterable[str],
) -> ResearchIntegrityFinding:
    completed = set(completed_run_ids)
    planned = set(stage.planned_run_ids)
    missing = sorted(planned - completed)
    if stage.completion_policy == "all_required" and missing:
        return ResearchIntegrityFinding(
            code="stage_completion",
            status="FAIL",
            message=f"required runs incomplete: {missing}",
        )
    return ResearchIntegrityFinding(
        code="stage_completion",
        status="PASS",
        message="completion policy satisfied",
    )
