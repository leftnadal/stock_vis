from pathlib import Path

from lab_automation.artifact_store import LocalArtifactStore
from lab_automation.research_runtime.contracts import (
    ExperimentProfile,
    ExposureProfile,
    InterpretationBoundary,
    StageProfile,
    WorkloadProfile,
)
from lab_automation.research_runtime.profile_io import store_profile_bundle


def test_research_profile_bundle_is_content_addressed(tmp_path: Path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    experiment = ExperimentProfile(
        experiment_id="EXP-1",
        purpose="critic calibration",
        validation_question="does independent criticism improve the draft?",
        experiment_class="critic_calibration",
        status="candidate",
        interpretation_boundary=InterpretationBoundary(
            prohibited_inferences=("Mac runtime performance",),
        ),
    )
    workload = WorkloadProfile(
        case_id="case-1",
        case_version="v1",
        task_ref="artifact://task",
        instruction_ref="artifact://instruction",
        evidence_snapshot_ref="artifact://evidence",
        evaluation_partition="calibration",
    )
    stage = StageProfile(
        stage_id="critic-stage",
        function="critic",
        planned_run_ids=("C1", "C2"),
        independence_intent="independent",
    )
    exposure = ExposureProfile(run_id="C1", evidence_refs=("artifact://evidence",))

    ref = store_profile_bundle(
        store,
        experiment,
        workloads=(workload,),
        stages=(stage,),
        exposures=(exposure,),
    )

    assert ref.kind == "research_experiment_profile"
    assert store.verify(ref)
