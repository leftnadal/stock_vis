"""Configurable-model Research Runtime vertical slice.

This experiment keeps the same bounded synthetic denominator-alignment workload
as the deterministic fixture pilot, but replaces fixture role execution with
configurable command backends. The harness preserves exact exposure and uses a
small deterministic benchmark only after model outputs are produced; the hidden
expectation is never included in model-visible inputs.
"""

from __future__ import annotations

from dataclasses import asdict, replace
import argparse
import json
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from lab_automation.artifact_store import ArtifactRef, LocalArtifactStore
from lab_automation.execution_records import InvocationRecord
from lab_automation.ledger import AppendOnlyLedger, RunEvent
from lab_automation.research_runtime.backends import (
    BackendExecution,
    BackendRequest,
    load_command_backend,
)
from lab_automation.research_runtime.contracts import (
    EvaluationLink,
    ExperimentProfile,
    ExposureProfile,
    InterpretationBoundary,
    RunLink,
    StageProfile,
    WorkloadProfile,
)
from lab_automation.research_runtime.preflight import (
    check_expected_answer_leakage,
    check_stage_completion,
    check_stage_independence,
)
from lab_automation.research_runtime.profile_io import store_profile_bundle

RUNNER_VERSION = "research-model-vertical-slice/0.1"
EXPERIMENT_ID = "SV-RES-RUNTIME-MODEL-E2E-001"
CASE_ID = "synthetic-denominator-alignment-001"
EVALUATION_METHODOLOGY_REF = "research_lab/02_evaluation/evaluation_methodology.md"


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


def _claim_value(output: Mapping[str, Any], key: str) -> float:
    claims = output.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("output must contain object field 'claims'")
    value = claims.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"claims.{key} must be numeric")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"claims.{key} must be between 0 and 1")
    return value


def _validate_role_output(role: str, output: Mapping[str, Any]) -> None:
    if role in {"researcher", "revision"}:
        _claim_value(output, "segment_a_total_share")
        _claim_value(output, "customer_z_total_share")
        return
    if role == "critic":
        findings = output.get("findings")
        if not isinstance(findings, list):
            raise ValueError("critic output must contain list field 'findings'")
        return
    if role == "evaluator":
        for key in (
            "repaired_errors",
            "preserved_correct_content",
            "introduced_errors",
            "unresolved_errors",
        ):
            if not isinstance(output.get(key), list):
                raise ValueError(f"evaluator output field '{key}' must be a list")
        if not isinstance(output.get("conclusion"), str):
            raise ValueError("evaluator output must contain string field 'conclusion'")
        return
    raise ValueError(f"unsupported role: {role}")


def _response_contract(role: str) -> dict[str, Any]:
    if role == "researcher":
        return {
            "claims": {
                "segment_a_total_share": "number in [0,1]",
                "customer_z_total_share": "number in [0,1]",
            },
            "reasoning_summary": "string",
            "uncertainty": ["string"],
        }
    if role == "critic":
        return {
            "findings": [
                {
                    "type": "repair|preserve|concern|no_change",
                    "target": "string",
                    "message": "string",
                }
            ],
            "proposed_revision": {
                "claims": {
                    "segment_a_total_share": "number in [0,1]",
                    "customer_z_total_share": "number in [0,1]",
                }
            },
        }
    if role == "revision":
        return {
            "claims": {
                "segment_a_total_share": "number in [0,1]",
                "customer_z_total_share": "number in [0,1]",
            },
            "conditions": ["string"],
            "uncertainty": ["string"],
        }
    if role == "evaluator":
        return {
            "repaired_errors": ["string"],
            "preserved_correct_content": ["string"],
            "introduced_errors": ["string"],
            "unresolved_errors": ["string"],
            "conclusion": "string",
        }
    raise ValueError(role)


def _instruction(role: str) -> str:
    instructions = {
        "researcher": (
            "Answer the question from the supplied task and evidence. Preserve source "
            "denominators, do not invent unsupported facts, and state uncertainty."
        ),
        "critic": (
            "Independently challenge the Researcher output against the task and evidence. "
            "Check denominator/scope alignment and preserve content that is already correct."
        ),
        "revision": (
            "Produce a revised answer using the original Researcher output, Critic output, "
            "and evidence. Apply only warranted repairs; do not add unsupported claims."
        ),
        "evaluator": (
            "Compare the baseline Researcher output and revised output against the evidence. "
            "Do not assume a Critic change is beneficial. Separate repaired, preserved, "
            "introduced, and unresolved content."
        ),
    }
    return instructions[role]


def _invoke_model(
    *,
    config_path: Path,
    store: LocalArtifactStore,
    ledger: AppendOnlyLedger,
    execution_id: str,
    run_id: str,
    role: str,
    payload: dict[str, Any],
    artifact_refs: tuple[str, ...],
    target_run_id: str | None = None,
) -> tuple[ArtifactRef, ArtifactRef, BackendExecution, InvocationRecord]:
    request = BackendRequest(
        role=role,
        run_id=run_id,
        instruction=_instruction(role),
        payload=payload,
        response_contract=_response_contract(role),
        metadata={"execution_id": execution_id, "experiment_id": EXPERIMENT_ID},
    )
    input_ref = _store_json(
        store,
        request.to_dict(),
        "research_model_input_snapshot",
        run_id=run_id,
        role=role,
    )
    backend = load_command_backend(config_path, role)
    execution = backend.execute(request)
    raw_execution_ref = _store_json(
        store,
        execution.to_dict(),
        "raw_backend_execution",
        run_id=run_id,
        role=role,
    )
    parsed_ref: ArtifactRef | None = None
    if execution.parsed_output is not None:
        parsed_ref = _store_json(
            store,
            dict(execution.parsed_output),
            "research_model_output",
            run_id=run_id,
            role=role,
        )

    invocation = InvocationRecord(
        run_id=run_id,
        actor=role,
        backend=execution.backend,
        execution_intent="primary",
        input_snapshot_ref=input_ref.logical_uri,
        output_ref=(
            parsed_ref.logical_uri
            if parsed_ref is not None
            else raw_execution_ref.logical_uri
        ),
        requested_identity=execution.requested_identity,
        returned_identity=execution.returned_identity,
        identity_assurance=execution.identity_assurance,
        started_at=execution.started_at,
        ended_at=execution.ended_at,
        status=execution.status,
        finish_reason=execution.finish_reason,
        returncode=execution.returncode,
        metadata={
            "command": list(execution.command),
            "target_run_id": target_run_id,
            "raw_execution_ref": raw_execution_ref.logical_uri,
        },
    )
    invocation_ref = _store_json(
        store,
        invocation.to_dict(),
        "invocation_record",
        run_id=run_id,
        invocation_id=invocation.invocation_id,
    )
    event_refs = list(artifact_refs) + [
        input_ref.logical_uri,
        raw_execution_ref.logical_uri,
        invocation_ref.logical_uri,
    ]
    if parsed_ref is not None:
        event_refs.append(parsed_ref.logical_uri)
    ledger.append(
        RunEvent(
            job_id=EXPERIMENT_ID,
            run_id=run_id,
            stage=role,
            status=execution.status,
            actor=role,
            runner_version=RUNNER_VERSION,
            artifact_refs=tuple(event_refs),
            invocation_ids=(invocation.invocation_id,),
            input_snapshot_ref=input_ref.logical_uri,
            output_ref=(
                parsed_ref.logical_uri
                if parsed_ref is not None
                else raw_execution_ref.logical_uri
            ),
            error=execution.error,
            metadata={
                "target_run_id": target_run_id,
                "execution_id": execution_id,
                "backend": execution.backend,
                "requested_identity": execution.requested_identity,
                "identity_assurance": execution.identity_assurance,
            },
        )
    )
    if (
        execution.status != "completed"
        or parsed_ref is None
        or execution.parsed_output is None
    ):
        raise RuntimeError(
            f"{role} backend did not produce a valid JSON object: {execution.error}"
        )
    _validate_role_output(role, execution.parsed_output)
    return input_ref, parsed_ref, execution, invocation


def _benchmark_delta(
    evidence: Mapping[str, Any],
    baseline: Mapping[str, Any],
    revised: Mapping[str, Any],
) -> dict[str, Any]:
    expected = float(evidence["segment_a_total_share"]) * float(
        evidence["customer_z_share_of_segment_a"]
    )
    baseline_customer = _claim_value(baseline, "customer_z_total_share")
    revised_customer = _claim_value(revised, "customer_z_total_share")
    baseline_segment = _claim_value(baseline, "segment_a_total_share")
    revised_segment = _claim_value(revised, "segment_a_total_share")
    expected_segment = float(evidence["segment_a_total_share"])
    tol = 1e-9
    repaired: list[str] = []
    preserved: list[str] = []
    introduced: list[str] = []
    unresolved: list[str] = []
    if (
        abs(baseline_customer - expected) > tol
        and abs(revised_customer - expected) <= tol
    ):
        repaired.append("customer_z_total_share denominator mismatch")
    if (
        abs(baseline_segment - expected_segment) <= tol
        and abs(revised_segment - expected_segment) <= tol
    ):
        preserved.append("segment_a_total_share")
    if (
        abs(baseline_segment - expected_segment) <= tol
        and abs(revised_segment - expected_segment) > tol
    ):
        introduced.append("segment_a_total_share corrupted by revision")
    if abs(revised_customer - expected) > tol:
        unresolved.append("customer_z_total_share not aligned with nested shares")
    return {
        "expected_customer_z_total_share": expected,
        "baseline_customer_z_total_share": baseline_customer,
        "revised_customer_z_total_share": revised_customer,
        "repaired_errors": repaired,
        "preserved_correct_content": preserved,
        "introduced_errors": introduced,
        "unresolved_errors": unresolved,
        "net_direction": (
            "improved"
            if repaired and not introduced and not unresolved
            else "preserved_correct"
            if not repaired and not introduced and not unresolved
            else "not_improved"
        ),
    }


def run_model_vertical_slice(config_path: Path, state_root: Path) -> dict[str, Any]:
    state_root = state_root.expanduser().resolve()
    config_path = config_path.expanduser().resolve()
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
    }
    evidence = {
        "segment_a_total_share": 0.60,
        "customer_z_share_of_segment_a": 0.40,
        "period_alignment": "same synthetic period",
    }
    hidden_expectation = {
        "customer_z_total_share_under_declared_assumptions": 0.24,
        "note": "Harness-only benchmark material. Never model-visible.",
    }
    task_ref = _store_json(
        store, task, "research_task", experiment_id=EXPERIMENT_ID
    )
    evidence_ref = _store_json(
        store, evidence, "evidence_snapshot", experiment_id=EXPERIMENT_ID
    )
    expectation_ref = _store_json(
        store,
        hidden_expectation,
        "protected_expectation",
        experiment_id=EXPERIMENT_ID,
    )

    experiment = ExperimentProfile(
        experiment_id=EXPERIMENT_ID,
        purpose=(
            "Exercise the Researcher → Critic → Revision → Evaluator lineage with "
            "configurable external/local command backends on the same synthetic case."
        ),
        validation_question=(
            "Does provenance, exposure, target lineage, and evaluation separation remain "
            "reconstructable when deterministic fixtures are replaced by real model calls?"
        ),
        experiment_class="model_runtime_vertical_slice",
        status="running",
        scope=(
            "Synthetic denominator-alignment workload with configurable command backends."
        ),
        known_confounds=(
            "One synthetic workload cannot establish general model capability.",
            "Backend/provider/model settings may differ across roles.",
        ),
        interpretation_boundary=InterpretationBoundary(
            allowed_inferences=(
                "Whether the configured backend can complete the bounded runtime contract.",
                (
                    "Whether Critic/Revision changed the synthetic answer in a "
                    "benchmarkable way."
                ),
            ),
            prohibited_inferences=(
                "General superiority of any model or provider.",
                "Mac Studio performance or production research readiness.",
            ),
        ),
        metadata={"execution_id": execution_id, "backend_config": str(config_path)},
    )
    workload = WorkloadProfile(
        case_id=CASE_ID,
        case_version="0.1",
        task_ref=task_ref.logical_uri,
        instruction_ref="role-specific instructions embedded in model input snapshots",
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
    exposures: list[ExposureProfile] = []
    run_links: list[RunLink] = []
    completed: list[str] = []

    try:
        researcher_exposure = ExposureProfile(
            run_id=run_ids["researcher"],
            evidence_refs=(evidence_ref.logical_uri,),
            other_material_refs=(task_ref.logical_uri,),
        )
        exposures.append(researcher_exposure)
        r_in, r_out, _, _ = _invoke_model(
            config_path=config_path,
            store=store,
            ledger=ledger,
            execution_id=execution_id,
            run_id=run_ids["researcher"],
            role="researcher",
            payload={"task": task, "evidence": evidence},
            artifact_refs=(task_ref.logical_uri, evidence_ref.logical_uri),
        )
        researcher_output = json.loads(
            store.path_for(r_out).read_text(encoding="utf-8")
        )
        run_links.append(
            RunLink(
                run_ids["researcher"],
                "researcher",
                input_snapshot_ref=r_in.logical_uri,
            )
        )
        completed.append(run_ids["researcher"])

        critic_exposure = ExposureProfile(
            run_id=run_ids["critic"],
            evidence_refs=(evidence_ref.logical_uri,),
            prior_run_refs=(run_ids["researcher"],),
            other_material_refs=(task_ref.logical_uri, r_out.logical_uri),
        )
        exposures.append(critic_exposure)
        c_in, c_out, _, _ = _invoke_model(
            config_path=config_path,
            store=store,
            ledger=ledger,
            execution_id=execution_id,
            run_id=run_ids["critic"],
            role="critic",
            payload={
                "task": task,
                "evidence": evidence,
                "researcher_output": researcher_output,
            },
            artifact_refs=(
                task_ref.logical_uri,
                evidence_ref.logical_uri,
                r_out.logical_uri,
            ),
            target_run_id=run_ids["researcher"],
        )
        critic_output = json.loads(store.path_for(c_out).read_text(encoding="utf-8"))
        run_links.append(
            RunLink(
                run_ids["critic"],
                "critic",
                target_run_id=run_ids["researcher"],
                target_artifact_hash=r_out.sha256,
                input_snapshot_ref=c_in.logical_uri,
            )
        )
        completed.append(run_ids["critic"])

        revision_exposure = ExposureProfile(
            run_id=run_ids["revision"],
            evidence_refs=(evidence_ref.logical_uri,),
            prior_run_refs=(run_ids["researcher"], run_ids["critic"]),
            other_material_refs=(r_out.logical_uri, c_out.logical_uri),
        )
        exposures.append(revision_exposure)
        v_in, v_out, _, _ = _invoke_model(
            config_path=config_path,
            store=store,
            ledger=ledger,
            execution_id=execution_id,
            run_id=run_ids["revision"],
            role="revision",
            payload={
                "task": task,
                "evidence": evidence,
                "researcher_output": researcher_output,
                "critic_output": critic_output,
            },
            artifact_refs=(
                evidence_ref.logical_uri,
                r_out.logical_uri,
                c_out.logical_uri,
            ),
            target_run_id=run_ids["researcher"],
        )
        revised_output = json.loads(
            store.path_for(v_out).read_text(encoding="utf-8")
        )
        run_links.append(
            RunLink(
                run_ids["revision"],
                "revision",
                target_run_id=run_ids["researcher"],
                target_artifact_hash=r_out.sha256,
                input_snapshot_ref=v_in.logical_uri,
            )
        )
        completed.append(run_ids["revision"])

        evaluator_exposure = ExposureProfile(
            run_id=run_ids["evaluator"],
            evidence_refs=(evidence_ref.logical_uri,),
            prior_run_refs=(run_ids["researcher"], run_ids["revision"]),
            other_material_refs=(r_out.logical_uri, v_out.logical_uri),
        )
        exposures.append(evaluator_exposure)
        e_in, e_out, _, _ = _invoke_model(
            config_path=config_path,
            store=store,
            ledger=ledger,
            execution_id=execution_id,
            run_id=run_ids["evaluator"],
            role="evaluator",
            payload={
                "task": task,
                "evidence": evidence,
                "baseline_output": researcher_output,
                "revised_output": revised_output,
            },
            artifact_refs=(
                evidence_ref.logical_uri,
                r_out.logical_uri,
                v_out.logical_uri,
            ),
            target_run_id=run_ids["revision"],
        )
        evaluator_output = json.loads(
            store.path_for(e_out).read_text(encoding="utf-8")
        )
        run_links.append(
            RunLink(
                run_ids["evaluator"],
                "evaluator",
                target_run_id=run_ids["revision"],
                target_artifact_hash=v_out.sha256,
                input_snapshot_ref=e_in.logical_uri,
            )
        )
        completed.append(run_ids["evaluator"])

        benchmark = _benchmark_delta(evidence, researcher_output, revised_output)
        benchmark_ref = _store_json(
            store,
            benchmark,
            "synthetic_harness_benchmark",
            experiment_id=EXPERIMENT_ID,
            execution_id=execution_id,
        )
        evaluation_link = EvaluationLink(
            evaluation_id=f"eval-{execution_id}",
            purpose="critic_revision_delta",
            target_run_id=run_ids["revision"],
            target_artifact_hash=v_out.sha256,
            evaluator_run_id=run_ids["evaluator"],
            methodology_ref=EVALUATION_METHODOLOGY_REF,
            metadata={"benchmark_ref": benchmark_ref.logical_uri},
        )

        findings: list[dict[str, Any]] = []
        for exposure in exposures:
            findings.append(asdict(check_expected_answer_leakage(workload, exposure)))
        findings.append(
            asdict(
                check_stage_independence(
                    stages[1], {item.run_id: item for item in exposures}
                )
            )
        )
        for stage in stages:
            findings.append(asdict(check_stage_completion(stage, completed)))
        evaluator_saw_critic = (
            run_ids["critic"] in evaluator_exposure.prior_run_refs
            or c_out.logical_uri in evaluator_exposure.all_refs()
        )
        findings.append(
            {
                "code": "evaluator_critic_reasoning_separation",
                "status": "FAIL" if evaluator_saw_critic else "PASS",
                "message": (
                    "evaluator was exposed to critic output"
                    if evaluator_saw_critic
                    else (
                        "evaluator saw baseline, revision, and evidence without "
                        "critic output"
                    )
                ),
            }
        )
        blocking = [row for row in findings if row["status"] == "FAIL"]
        experiment = replace(
            experiment,
            status="completed" if not blocking else "integrity_failed",
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
            "schema_version": "research-model-vertical-slice-summary/0.1",
            "experiment_id": EXPERIMENT_ID,
            "execution_id": execution_id,
            "status": experiment.status,
            "profile_ref": profile_ref.logical_uri,
            "benchmark_ref": benchmark_ref.logical_uri,
            "benchmark": benchmark,
            "evaluator_output": evaluator_output,
            "integrity_findings": findings,
            "blocking_failures": blocking,
            "run_ids": run_ids,
            "interpretation_limits": list(
                experiment.interpretation_boundary.prohibited_inferences
            ),
        }
        summary_ref = _store_json(
            store,
            summary,
            "research_model_vertical_slice_summary",
            experiment_id=EXPERIMENT_ID,
            execution_id=execution_id,
        )
        summary_dir = (
            state_root / "research_runtime" / EXPERIMENT_ID / execution_id
        )
        summary_dir.mkdir(parents=True, exist_ok=True)
        (summary_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ledger.append(
            RunEvent(
                job_id=EXPERIMENT_ID,
                run_id=execution_id,
                stage="experiment_summary",
                status=experiment.status,
                actor="research_runtime",
                runner_version=RUNNER_VERSION,
                artifact_refs=(
                    profile_ref.logical_uri,
                    benchmark_ref.logical_uri,
                    summary_ref.logical_uri,
                ),
                metadata={"blocking_failure_count": len(blocking)},
            )
        )
        return summary
    except Exception as exc:
        ledger.append(
            RunEvent(
                job_id=EXPERIMENT_ID,
                run_id=execution_id,
                stage="terminal",
                status="failed",
                actor="research_runtime",
                runner_version=RUNNER_VERSION,
                error=f"{type(exc).__name__}: {exc}",
                metadata={"completed_run_ids": completed},
            )
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path.home() / ".stockvis-lab-automation",
    )
    args = parser.parse_args()
    summary = run_model_vertical_slice(args.config, args.state_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["blocking_failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
