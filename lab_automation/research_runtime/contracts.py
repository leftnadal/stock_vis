"""Research Experiment Profile v0.1 contracts.

These records sit on top of the shared Lab Automation Run Ledger. They describe
research-experiment semantics such as workload identity, exposure, blinding,
independence intent, and evaluation linkage. They are operational candidates,
not new Research Lab epistemic object types or methodology.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


EVALUATION_PARTITIONS = {
    "development",
    "calibration",
    "validation",
    "protected_holdout",
}


@dataclass(frozen=True)
class InterpretationBoundary:
    allowed_inferences: tuple[str, ...] = field(default_factory=tuple)
    prohibited_inferences: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExperimentProfile:
    experiment_id: str
    purpose: str
    validation_question: str
    experiment_class: str
    status: str
    scope: str = ""
    known_confounds: tuple[str, ...] = field(default_factory=tuple)
    interpretation_boundary: InterpretationBoundary = field(
        default_factory=InterpretationBoundary
    )
    schema_version: str = "research-experiment/0.1"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkloadProfile:
    case_id: str
    case_version: str
    task_ref: str
    instruction_ref: str
    evidence_snapshot_ref: str
    evaluation_partition: str = "development"
    protected_expectation_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.evaluation_partition not in EVALUATION_PARTITIONS:
            raise ValueError(
                f"invalid evaluation_partition: {self.evaluation_partition}"
            )


@dataclass(frozen=True)
class StageProfile:
    stage_id: str
    function: str
    planned_run_ids: tuple[str, ...] = field(default_factory=tuple)
    completion_policy: str = "all_required"
    independence_intent: str = "not_declared"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunLink:
    run_id: str
    stage_id: str
    target_run_id: str | None = None
    target_artifact_hash: str | None = None
    input_snapshot_ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExposureProfile:
    run_id: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    prior_run_refs: tuple[str, ...] = field(default_factory=tuple)
    retrieved_learning_refs: tuple[str, ...] = field(default_factory=tuple)
    tool_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    other_material_refs: tuple[str, ...] = field(default_factory=tuple)

    def all_refs(self) -> set[str]:
        return set(
            self.evidence_refs
            + self.prior_run_refs
            + self.retrieved_learning_refs
            + self.tool_artifact_refs
            + self.other_material_refs
        )


@dataclass(frozen=True)
class EvaluationLink:
    evaluation_id: str
    purpose: str
    target_run_id: str
    target_artifact_hash: str | None
    evaluator_run_id: str
    methodology_ref: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
