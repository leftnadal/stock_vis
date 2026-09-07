"""Serialization helpers for Research Experiment Profile v0.1."""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from lab_automation.artifact_store import ArtifactRef, LocalArtifactStore
from lab_automation.research_runtime.contracts import (
    EvaluationLink,
    ExperimentProfile,
    ExposureProfile,
    RunLink,
    StageProfile,
    WorkloadProfile,
)


def build_profile_bundle(
    experiment: ExperimentProfile,
    *,
    workloads: Iterable[WorkloadProfile] = (),
    stages: Iterable[StageProfile] = (),
    run_links: Iterable[RunLink] = (),
    exposures: Iterable[ExposureProfile] = (),
    evaluations: Iterable[EvaluationLink] = (),
) -> dict:
    return {
        "schema_version": "research-experiment-bundle/0.1",
        "experiment": asdict(experiment),
        "workloads": [asdict(item) for item in workloads],
        "stages": [asdict(item) for item in stages],
        "run_links": [asdict(item) for item in run_links],
        "exposures": [asdict(item) for item in exposures],
        "evaluations": [asdict(item) for item in evaluations],
    }


def store_profile_bundle(
    store: LocalArtifactStore,
    experiment: ExperimentProfile,
    *,
    workloads: Iterable[WorkloadProfile] = (),
    stages: Iterable[StageProfile] = (),
    run_links: Iterable[RunLink] = (),
    exposures: Iterable[ExposureProfile] = (),
    evaluations: Iterable[EvaluationLink] = (),
) -> ArtifactRef:
    bundle = build_profile_bundle(
        experiment,
        workloads=workloads,
        stages=stages,
        run_links=run_links,
        exposures=exposures,
        evaluations=evaluations,
    )
    return store.put_json(
        bundle,
        kind="research_experiment_profile",
        retention_class="irreplaceable",
        metadata={"experiment_id": experiment.experiment_id},
    )
