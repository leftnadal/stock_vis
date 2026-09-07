from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from lab_automation.artifact_store import ArtifactRef, LocalArtifactStore
from lab_automation.execution_records import InvocationRecord
from lab_automation.ledger import AppendOnlyLedger, RunEvent
from lab_automation.research_runtime.contracts import (
    EvaluationLink, ExperimentProfile, ExposureProfile, InterpretationBoundary,
    RunLink, StageProfile, WorkloadProfile,
)
from lab_automation.research_runtime.preflight import (
    check_expected_answer_leakage, check_stage_completion, check_stage_independence,
)
from lab_automation.research_runtime.profile_io import store_profile_bundle

RUNNER_VERSION = "research-vertical-slice/0.1"
EXPERIMENT_ID = "SV-RES-RUNTIME-E2E-001"
CASE_ID = "synthetic-denominator-alignment-001"
EVALUATION_METHODOLOGY_REF = "research_lab/02_evaluation/evaluation_methodology.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_json(
    store: LocalArtifactStore,
    payload: Any,
    kind: str,
    **metadata: Any,
) -> ArtifactRef:
    return store.put_json(
        payload,
        kind=kind,
        retention_class="irreplaceable",
        metadata=metadata,
    )


def _invoke_fixture(
    *,
    store: LocalArtifactStore,
    ledger: AppendOnlyLedger,
    execution_id: str,
    run_id: str,
    stage_id: str,
    actor: str,
    input_payload: dict[str, Any],
    output_builder: Callable[[dict[str, Any]], dict[str, Any]],
    artifact_refs: tuple[str, ...],
    target_run_id: str | None = None,
) -> tuple[ArtifactRef, ArtifactRef, InvocationRecord]:
    input_ref = _store_json(
        store,
        input_payload,
        "research_fixture_input_snapshot",
        run_id=run_id,
        actor=actor,
    )
    started = _now()
    output = output_builder(input_payload)
    ended = _now()
    output_ref = _store_json(
        store,
        output,
        "research_fixture_output",
        run_id=run_id,
        actor=actor,
    )
    invocation = InvocationRecord(
        run_id=run_id,
        actor=actor,
        backend="deterministic_fixture",
        execution_intent="primary",
        input_snapshot_ref=input_ref.logical_uri,
        output_ref=output_ref.logical_uri,
        requested_identity=f"{actor}/fixture-v0.1",
        returned_identity=f"{actor}/fixture-v0.1",
        identity_assurance="artifact_verified",
        started_at=started,
        ended_at=ended,
        status="completed",
        finish_reason="fixture_complete",
        returncode=0,
    )
    invocation_ref = _store_json(
        store,
        invocation.to_dict(),
        "invocation_record",
        run_id=run_id,
        invocation_id=invocation.invocation_id,
    )
    ledger.append(
        RunEvent(
            job_id=EXPERIMENT_ID,
            run_id=run_id,
            stage=stage_id,
            status="completed",
            actor=actor,
            runner_version=RUNNER_VERSION,
            artifact_refs=artifact_refs
            + (
                input_ref.logical_uri,
                output_ref.logical_uri,
                invocation_ref.logical_uri,
            ),
            invocation_ids=(invocation.invocation_id,),
            input_snapshot_ref=input_ref.logical_uri,
            output_ref=output_ref.logical_uri,
            metadata={
                "target_run_id": target_run_id,
                "execution_id": execution_id,
            },
        )
    )
    return input_ref, output_ref, invocation


def _researcher(_: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "synthetic-researcher-output/0.1",
        "claims": {
            "segment_a_total_share": 0.60,
            "customer_z_total_share": 0.40,
        },
        "reasoning_summary": (
            "The researcher incorrectly treated Customer Z's 40% share of Segment A "
            "as 40% of total company revenue."
        ),
        "uncertainty": [],
    }


def _critic(payload: dict[str, Any]) -> dict[str, Any]:
    original = payload["researcher_output"]
    return {
        "schema_version": "synthetic-critic-output/0.1",
        "findings": [
            {
                "type": "repair",
                "target": "customer_z_total_share",
                "message": (
                    "The 40% source uses Segment A as the denominator, not total revenue. "
                    "With Segment A at 60% of total revenue, implied total exposure is 24% "
                    "if the shares are exact and nested."
                ),
            },
            {
                "type": "preserve",
                "target": "segment_a_total_share",
                "message": (
                    "The 60% Segment A share is directly supported by the evidence."
                ),
            },
        ],
        "proposed_customer_z_total_share": 0.24,
        "source_baseline": original["claims"],
    }


def _revision(payload: dict[str, Any]) -> dict[str, Any]:
    original = payload["researcher_output"]
    critic = payload["critic_output"]
    return {
        "schema_version": "synthetic-revision-output/0.1",
        "claims": {
            "segment_a_total_share": original["claims"]["segment_a_total_share"],
            "customer_z_total_share": critic["proposed_customer_z_total_share"],
        },
        "conditions": [
            "Customer Z's 40% share is interpreted as an exact share of Segment A revenue.",
            "Segment A's 60% share is interpreted as an exact share of total revenue.",
        ],
        "uncertainty": [
            "If the source scopes or periods are not aligned, 24% should not be treated as exact."
        ],
    }


def _evaluator(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = payload["evidence"]
    baseline = payload["baseline_output"]
    revised = payload["revised_output"]
    expected_customer_share = round(
        evidence["segment_a_total_share"]
        * evidence["customer_z_share_of_segment_a"],
        10,
    )
    repaired: list[str] = []
    preserved: list[str] = []
    introduced: list[str] = []
    unresolved: list[str] = []

    if (
        baseline["claims"]["customer_z_total_share"] != expected_customer_share
        and revised["claims"]["customer_z_total_share"] == expected_customer_share
    ):
        repaired.append("customer_z_total_share denominator mismatch")
    if (
        baseline["claims"]["segment_a_total_share"]
        == evidence["segment_a_total_share"]
        and revised["claims"]["segment_a_total_share"]
        == evidence["segment_a_total_share"]
    ):
        preserved.append("segment_a_total_share")
    if revised["claims"]["customer_z_total_share"] != expected_customer_share:
        unresolved.append("customer_z_total_share remains misaligned")
    if (
        revised["claims"]["segment_a_total_share"]
        != evidence["segment_a_total_share"]
    ):
        introduced.append("segment_a_total_share was corrupted")

    conclusion = (
        "improved" if repaired and not introduced and not unresolved else "not_improved"
    )
    return {
        "schema_version": "synthetic-evaluation-output/0.1",
        "evaluation_purpose": "critic_revision_delta",
        "expected_customer_z_total_share_under_declared_assumptions": (
            expected_customer_share
        ),
        "repaired_errors": repaired,
        "preserved_correct_content": preserved,
        "introduced_errors": introduced,
        "unresolved_errors": unresolved,
        "conclusion": conclusion,
    }


def run_vertical_slice(state_root: Path) -> dict[str, Any]:
    state_root = state_root.expanduser().resolve()
    execution_id = str(uuid4())
    store = LocalArtifactStore(state_root / "artifacts")
    ledger = AppendOnlyLedger(
        state_root / "ledger" / f"{EXPERIMENT_ID}-{execution_id}.jsonl"
    )

    task = {
        "case_id": CASE_ID,
        "question": (
            "What share of total revenue is attributable to Customer Z under the "
            "supplied nested shares?"
        ),
        "instruction": (
            "Preserve source denominators and state material assumptions explicitly."
        ),
    }
    evidence = {
        "segment_a_total_share": 0.60,
        "customer_z_share_of_segment_a": 0.40,
        "period_alignment": "same synthetic period",
    }
    hidden_expectation = {
        "expected_customer_z_total_share": 0.24,
        "expected_critic_delta": {
            "repair": ["customer_z_total_share denominator mismatch"],
            "preserve": ["segment_a_total_share"],
            "introduced": [],
        },
    }
    researcher_instruction = {
        "role": "researcher",
        "instruction": "Answer from task + evidence only.",
    }
    critic_instruction = {
        "role": "critic",
        "instruction": (
            "Challenge denominator alignment and preserve supported content."
        ),
    }
    revision_instruction = {
        "role": "revision",
        "instruction": "Apply only warranted critic repairs.",
    }
    evaluator_instruction = {
        "role": "evaluator",
        "instruction": (
            "Compare baseline and revision against evidence without reading critic "
            "reasoning."
        ),
    }

    task_ref = _store_json(
        store,
        task,
        "research_task",
        experiment_id=EXPERIMENT_ID,
    )
    evidence_ref = _store_json(
        store,
        evidence,
        "evidence_snapshot",
        experiment_id=EXPERIMENT_ID,
    )
    expectation_ref = _store_json(
        store,
        hidden_expectation,
        "protected_expectation",
        experiment_id=EXPERIMENT_ID,
    )
    researcher_instruction_ref = _store_json(
        store,
        researcher_instruction,
        "instruction",
        role="researcher",
    )
    critic_instruction_ref = _store_json(
        store,
        critic_instruction,
        "instruction",
        role="critic",
    )
    revision_instruction_ref = _store_json(
        store,
        revision_instruction,
        "instruction",
        role="revision",
    )
    evaluator_instruction_ref = _store_json(
        store,
        evaluator_instruction,
        "instruction",
        role="evaluator",
    )

    experiment = ExperimentProfile(
        experiment_id=EXPERIMENT_ID,
        purpose=(
            "Exercise the first complete Researcher → Critic → Revision → Evaluator "
            "runtime lineage on a bounded synthetic case."
        ),
        validation_question=(
            "Can the Research Experiment Profile reconstruct exposure and demonstrate "
            "a critic repair without answer leakage or target drift?"
        ),
        experiment_class="runtime_vertical_slice",
        status="running",
        scope="Synthetic denominator-alignment case; deterministic fixture backend only.",
        known_confounds=(
            "Deterministic fixture outputs do not measure LLM capability.",
            "Synthetic evidence does not measure external-source acquisition quality.",
        ),
        interpretation_boundary=InterpretationBoundary(
            allowed_inferences=(
                "The shared runtime can preserve material lineage for this vertical slice.",
                (
                    "The evaluator can distinguish repaired, preserved, introduced, and "
                    "unresolved content in this fixture."
                ),
            ),
            prohibited_inferences=(
                "Any local or Frontier model is validated by this fixture.",
                "The runtime is ready for unsupervised production research.",
            ),
        ),
        metadata={"execution_id": execution_id},
    )
    workload = WorkloadProfile(
        case_id=CASE_ID,
        case_version="0.1",
        task_ref=task_ref.logical_uri,
        instruction_ref=researcher_instruction_ref.logical_uri,
        evidence_snapshot_ref=evidence_ref.logical_uri,
        evaluation_partition="calibration",
        protected_expectation_refs=(expectation_ref.logical_uri,),
        metadata={"execution_id": execution_id},
    )

    run_ids = {
        name: str(uuid4())
        for name in ("researcher", "critic", "revision", "evaluator")
    }
    stages = (
        StageProfile(
            "researcher",
            "Researcher",
            (run_ids["researcher"],),
            "all_required",
            "not_declared",
        ),
        StageProfile(
            "critic",
            "Critic",
            (run_ids["critic"],),
            "all_required",
            "independent",
        ),
        StageProfile(
            "revision",
            "Revision",
            (run_ids["revision"],),
            "all_required",
            "not_declared",
        ),
        StageProfile(
            "evaluator",
            "Evaluator",
            (run_ids["evaluator"],),
            "all_required",
            "not_declared",
        ),
    )

    researcher_exposure = ExposureProfile(
        run_id=run_ids["researcher"],
        evidence_refs=(evidence_ref.logical_uri,),
        other_material_refs=(
            task_ref.logical_uri,
            researcher_instruction_ref.logical_uri,
        ),
    )
    r_in, r_out, _ = _invoke_fixture(
        store=store,
        ledger=ledger,
        execution_id=execution_id,
        run_id=run_ids["researcher"],
        stage_id="researcher",
        actor="researcher_fixture",
        input_payload={
            "task": task,
            "evidence": evidence,
            "instruction": researcher_instruction,
        },
        output_builder=_researcher,
        artifact_refs=(
            task_ref.logical_uri,
            evidence_ref.logical_uri,
            researcher_instruction_ref.logical_uri,
        ),
    )
    researcher_output = json.loads(store.path_for(r_out).read_text())

    critic_exposure = ExposureProfile(
        run_id=run_ids["critic"],
        evidence_refs=(evidence_ref.logical_uri,),
        prior_run_refs=(run_ids["researcher"],),
        other_material_refs=(
            task_ref.logical_uri,
            critic_instruction_ref.logical_uri,
            r_out.logical_uri,
        ),
    )
    c_in, c_out, _ = _invoke_fixture(
        store=store,
        ledger=ledger,
        execution_id=execution_id,
        run_id=run_ids["critic"],
        stage_id="critic",
        actor="critic_fixture",
        input_payload={
            "task": task,
            "evidence": evidence,
            "researcher_output": researcher_output,
            "instruction": critic_instruction,
        },
        output_builder=_critic,
        artifact_refs=(
            task_ref.logical_uri,
            evidence_ref.logical_uri,
            critic_instruction_ref.logical_uri,
            r_out.logical_uri,
        ),
        target_run_id=run_ids["researcher"],
    )
    critic_output = json.loads(store.path_for(c_out).read_text())

    revision_exposure = ExposureProfile(
        run_id=run_ids["revision"],
        evidence_refs=(evidence_ref.logical_uri,),
        prior_run_refs=(run_ids["researcher"], run_ids["critic"]),
        other_material_refs=(
            revision_instruction_ref.logical_uri,
            r_out.logical_uri,
            c_out.logical_uri,
        ),
    )
    v_in, v_out, _ = _invoke_fixture(
        store=store,
        ledger=ledger,
        execution_id=execution_id,
        run_id=run_ids["revision"],
        stage_id="revision",
        actor="revision_fixture",
        input_payload={
            "evidence": evidence,
            "researcher_output": researcher_output,
            "critic_output": critic_output,
            "instruction": revision_instruction,
        },
        output_builder=_revision,
        artifact_refs=(
            evidence_ref.logical_uri,
            revision_instruction_ref.logical_uri,
            r_out.logical_uri,
            c_out.logical_uri,
        ),
        target_run_id=run_ids["researcher"],
    )
    revision_output = json.loads(store.path_for(v_out).read_text())

    evaluator_exposure = ExposureProfile(
        run_id=run_ids["evaluator"],
        evidence_refs=(evidence_ref.logical_uri,),
        prior_run_refs=(run_ids["researcher"], run_ids["revision"]),
        other_material_refs=(
            evaluator_instruction_ref.logical_uri,
            r_out.logical_uri,
            v_out.logical_uri,
        ),
    )
    e_in, e_out, _ = _invoke_fixture(
        store=store,
        ledger=ledger,
        execution_id=execution_id,
        run_id=run_ids["evaluator"],
        stage_id="evaluator",
        actor="evaluator_fixture",
        input_payload={
            "evidence": evidence,
            "baseline_output": researcher_output,
            "revised_output": revision_output,
            "instruction": evaluator_instruction,
        },
        output_builder=_evaluator,
        artifact_refs=(
            evidence_ref.logical_uri,
            evaluator_instruction_ref.logical_uri,
            r_out.logical_uri,
            v_out.logical_uri,
        ),
        target_run_id=run_ids["revision"],
    )
    evaluation_output = json.loads(store.path_for(e_out).read_text())

    exposures = (
        researcher_exposure,
        critic_exposure,
        revision_exposure,
        evaluator_exposure,
    )
    exposure_by_run = {item.run_id: item for item in exposures}
    run_links = (
        RunLink(
            run_ids["researcher"],
            "researcher",
            input_snapshot_ref=r_in.logical_uri,
        ),
        RunLink(
            run_ids["critic"],
            "critic",
            target_run_id=run_ids["researcher"],
            target_artifact_hash=r_out.sha256,
            input_snapshot_ref=c_in.logical_uri,
        ),
        RunLink(
            run_ids["revision"],
            "revision",
            target_run_id=run_ids["researcher"],
            target_artifact_hash=r_out.sha256,
            input_snapshot_ref=v_in.logical_uri,
        ),
        RunLink(
            run_ids["evaluator"],
            "evaluator",
            target_run_id=run_ids["revision"],
            target_artifact_hash=v_out.sha256,
            input_snapshot_ref=e_in.logical_uri,
        ),
    )
    evaluation_link = EvaluationLink(
        evaluation_id=f"eval-{uuid4()}",
        purpose="critic_revision_delta",
        target_run_id=run_ids["revision"],
        target_artifact_hash=v_out.sha256,
        evaluator_run_id=run_ids["evaluator"],
        methodology_ref=EVALUATION_METHODOLOGY_REF,
        metadata={
            "baseline_run_id": run_ids["researcher"],
            "evaluation_output_ref": e_out.logical_uri,
        },
    )

    findings = []
    for exposure in exposures:
        findings.append(asdict(check_expected_answer_leakage(workload, exposure)))
    for stage in stages:
        findings.append(asdict(check_stage_completion(stage, run_ids.values())))
    findings.append(
        asdict(check_stage_independence(stages[1], exposure_by_run))
    )

    blocking_failures = [
        item for item in findings if item["status"] == "FAIL"
    ]
    if (
        run_ids["critic"] in evaluator_exposure.prior_run_refs
        or c_out.logical_uri in evaluator_exposure.all_refs()
    ):
        blocking_failures.append(
            {
                "code": "evaluator_critic_anchoring",
                "status": "FAIL",
                "message": "Evaluator was exposed to critic output.",
            }
        )

    experiment = replace(
        experiment,
        status="completed" if not blocking_failures else "failed",
    )
    profile_ref = store_profile_bundle(
        store,
        experiment,
        workloads=(workload,),
        stages=stages,
        run_links=run_links,
        exposures=exposures,
        evaluations=(evaluation_link,),
    )

    summary = {
        "schema_version": "research-runtime-vertical-slice-summary/0.1",
        "experiment_id": EXPERIMENT_ID,
        "execution_id": execution_id,
        "case_id": CASE_ID,
        "status": experiment.status,
        "profile_ref": profile_ref.logical_uri,
        "evaluation_ref": e_out.logical_uri,
        "evaluation": evaluation_output,
        "integrity_findings": findings,
        "blocking_failures": blocking_failures,
        "run_ids": run_ids,
        "evaluator_exposed_to_critic": False,
        "interpretation_boundary": asdict(experiment.interpretation_boundary),
    }
    summary_ref = _store_json(
        store,
        summary,
        "research_vertical_slice_summary",
        experiment_id=EXPERIMENT_ID,
    )
    summary_dir = (
        state_root / "research_runtime" / EXPERIMENT_ID / execution_id
    )
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {**summary, "summary_ref": summary_ref.logical_uri},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    ledger.append(
        RunEvent(
            job_id=EXPERIMENT_ID,
            run_id=run_ids["evaluator"],
            stage="research_experiment_complete",
            status=experiment.status,
            actor="research_vertical_slice",
            runner_version=RUNNER_VERSION,
            artifact_refs=(
                profile_ref.logical_uri,
                e_out.logical_uri,
                summary_ref.logical_uri,
            ),
            output_ref=summary_ref.logical_uri,
            metadata={
                "summary_path": str(summary_path),
                "execution_id": execution_id,
            },
        )
    )
    return {
        **summary,
        "summary_ref": summary_ref.logical_uri,
        "summary_path": str(summary_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path.home() / ".stockvis-lab-automation",
    )
    args = parser.parse_args()
    result = run_vertical_slice(args.state_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
