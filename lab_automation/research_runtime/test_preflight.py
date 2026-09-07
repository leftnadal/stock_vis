from lab_automation.research_runtime.contracts import (
    ExposureProfile,
    StageProfile,
    WorkloadProfile,
)
from lab_automation.research_runtime.preflight import (
    check_expected_answer_leakage,
    check_holdout_contamination,
    check_stage_completion,
    check_stage_independence,
)


def workload(**overrides):
    values = dict(
        case_id="case-001",
        case_version="v1",
        task_ref="artifact://task",
        instruction_ref="artifact://instruction",
        evidence_snapshot_ref="artifact://evidence",
        evaluation_partition="calibration",
        protected_expectation_refs=("artifact://truth",),
    )
    values.update(overrides)
    return WorkloadProfile(**values)


def test_detects_expected_answer_leakage():
    exposure = ExposureProfile(
        run_id="R1",
        other_material_refs=("artifact://truth",),
    )
    finding = check_expected_answer_leakage(workload(), exposure)
    assert finding.status == "FAIL"


def test_independent_stage_rejects_peer_output_exposure():
    stage = StageProfile(
        stage_id="critic-stage",
        function="critic",
        planned_run_ids=("C1", "C2"),
        independence_intent="independent",
    )
    exposures = {
        "C1": ExposureProfile(run_id="C1"),
        "C2": ExposureProfile(run_id="C2", prior_run_refs=("C1",)),
    }
    finding = check_stage_independence(stage, exposures)
    assert finding.status == "FAIL"


def test_protected_holdout_detects_known_contamination():
    holdout = workload(evaluation_partition="protected_holdout")
    exposure = ExposureProfile(
        run_id="R1",
        retrieved_learning_refs=("artifact://contaminated",),
    )
    finding = check_holdout_contamination(
        holdout,
        exposure,
        contaminated_refs=("artifact://contaminated",),
    )
    assert finding.status == "FAIL"


def test_all_required_stage_requires_all_planned_runs():
    stage = StageProfile(
        stage_id="critic-stage",
        function="critic",
        planned_run_ids=("C1", "C2"),
        completion_policy="all_required",
    )
    finding = check_stage_completion(stage, completed_run_ids=("C1",))
    assert finding.status == "FAIL"
