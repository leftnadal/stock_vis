"""Minimal local runner for StockVis Lab Automation Platform.

Scope v0.1:
- load one local JSON job file
- create an isolated git worktree from the declared branch
- record authority refs and base SHA
- capture an immutable agent input snapshot
- invoke Codex CLI through a configurable command
- store raw invocation material in a content-addressed artifact store
- run declared test commands
- write structured review artifacts
- create one local candidate commit
- stop in `waiting_for_push_approval`

It intentionally does NOT push, open/merge PRs, deploy, or mutate production DB.
Runtime ledger/state are stored outside the repository checkout by default so the
main Claude Code workspace is not dirtied by automation telemetry.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any
from uuid import uuid4

from lab_automation.artifact_store import ArtifactRef, LocalArtifactStore
from lab_automation.contracts import JobEnvelope, JobStatus, Lab
from lab_automation.execution_records import InvocationRecord
from lab_automation.integrity import (
    require_output_contract,
    validate_json_artifact,
    validate_nonempty_text_artifact,
)
from lab_automation.ledger import AppendOnlyLedger, RunEvent

RUNNER_VERSION = "0.1.4"
REQUIRED_AGENT_ARTIFACTS = (
    "agent_report.md",
    "result.json",
    "data_gaps.json",
)


class CommandFailure(RuntimeError):
    """A failed external command whose captured diagnostics must survive."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        super().__init__(
            f"{payload['stage']} command failed with return code "
            f"{payload['returncode']}: {payload['command']}"
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(
    command: list[str],
    cwd: Path,
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        env=env,
    )


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd, check=check)


def _read_job(path: Path) -> tuple[JobEnvelope, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    envelope = JobEnvelope(
        job_id=raw["job_id"],
        lab=Lab(raw["lab"]),
        goal=raw["goal"],
        branch=raw["branch"],
        authority_refs=tuple(raw.get("authority_refs", [])),
        expected_outputs=tuple(raw.get("expected_outputs", [])),
        allowed_write_paths=tuple(raw.get("allowed_write_paths", [])),
        db_access=raw.get("db_access", "none"),
        network_policy=raw.get("network_policy", "restricted"),
        destructive_actions_allowed=bool(raw.get("destructive_actions_allowed", False)),
        status=JobStatus(raw.get("status", "queued")),
        parent_job_ids=tuple(raw.get("parent_job_ids", [])),
    )
    return envelope, raw


def _validate_job(job: JobEnvelope) -> None:
    if job.destructive_actions_allowed:
        raise ValueError("v0.1 runner refuses destructive_actions_allowed=true")
    if job.db_access not in {"none", "read_only"}:
        raise ValueError("v0.1 runner allows only db_access=none/read_only")
    if not job.allowed_write_paths:
        raise ValueError("allowed_write_paths must not be empty")
    if job.branch in {"main", "master"}:
        raise ValueError("runner refuses direct execution on main/master")


def _current_sha(repo: Path, ref: str = "HEAD") -> str:
    return _git(repo, "rev-parse", ref).stdout.strip()


def _safe_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value)


def _worktree_path(root: Path, job_id: str, run_id: str) -> Path:
    return root / f"{_safe_token(job_id)}-{run_id[:8]}"


def _candidate_branch(job_id: str, run_id: str) -> str:
    return f"lab-run/{_safe_token(job_id)}/{run_id[:8]}"


def _authority_snapshot(worktree: Path, refs: tuple[str, ...], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[Path] = []
    for ref in refs:
        source = worktree / ref
        if not source.is_file():
            raise FileNotFoundError(f"authority ref not found: {ref}")
        target = output_dir / ref.replace("/", "__")
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        artifacts.append(target)
    return artifacts


def _build_codex_prompt(job: JobEnvelope, result_dir: Path) -> str:
    authority = "\n".join(f"- {x}" for x in job.authority_refs)
    expected = "\n".join(f"- {x}" for x in job.expected_outputs)
    writes = "\n".join(f"- {x}" for x in job.allowed_write_paths)
    return f"""You are executing StockVis Lab Automation job {job.job_id}.
Lab: {job.lab.value}
Goal: {job.goal}

Authority references you must read:
{authority}

Allowed write paths only:
{writes}

Expected outputs:
{expected}

Constraints:
- This Job already authorizes local implementation and validation within the declared scope.
- Do not pause or ask for another approval; proceed with the authorized local work.
- Do not push, merge, deploy, force-push, or modify main/master.
- DB access policy: {job.db_access}.
- Network policy: {job.network_policy}.
- Do not perform destructive actions.
- Record failures and uncertainty; do not hide unsuccessful attempts.
- The three result paths below are runner-designated output locations authorized in addition to the Job write scope.
- Write a concise execution report to: {result_dir / 'agent_report.md'}
- Write machine-readable findings to: {result_dir / 'result.json'}
- Write machine-readable data gaps to: {result_dir / 'data_gaps.json'}
- All three result artifacts are required. Use valid JSON and write [] to data_gaps.json when no gaps are found.
- result.json must contain findings and must not be an empty JSON object.
"""


def _invoke_codex(
    worktree: Path,
    job: JobEnvelope,
    raw: dict[str, Any],
    prompt: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    command_template = raw.get("codex_command", ["codex", "exec", "-"])
    command = shlex.split(command_template) if isinstance(command_template, str) else list(command_template)
    if dry_run:
        return {
            "command": command,
            "dry_run": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
        }
    env = os.environ.copy()
    env["STOCKVIS_LAB_JOB_ID"] = job.job_id
    env["STOCKVIS_LAB_DB_ACCESS"] = job.db_access
    proc = subprocess.run(
        command,
        cwd=str(worktree),
        input=prompt,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    return {
        "command": command,
        "dry_run": False,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }


def _run_tests(worktree: Path, raw: dict[str, Any], dry_run: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in raw.get("test_commands", []):
        command = shlex.split(item) if isinstance(item, str) else list(item)
        if dry_run:
            results.append({"command": command, "returncode": 0, "dry_run": True})
            continue
        proc = _run(command, worktree, check=False)
        results.append(
            {
                "command": command,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "dry_run": False,
            }
        )
    return results


def _changed_paths(worktree: Path) -> list[str]:
    proc = _git(worktree, "status", "--porcelain", "--untracked-files=all")
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if line.strip():
            paths.append(line[3:].strip())
    return paths


def _path_allowed(path: str, allowed: tuple[str, ...]) -> bool:
    normalized = path.rstrip("/")
    for prefix in allowed:
        normalized_prefix = prefix.rstrip("/")
        if normalized == normalized_prefix or normalized.startswith(normalized_prefix + "/"):
            return True
    return False


def _enforce_write_scope(paths: list[str], allowed: tuple[str, ...]) -> None:
    disallowed = [path for path in paths if not _path_allowed(path, allowed)]
    if disallowed:
        raise PermissionError(f"write-scope violation: {disallowed}")


def _meaningful_changed_paths(
    paths: list[str],
    allowed: tuple[str, ...],
) -> list[str]:
    return [
        path
        for path in paths
        if _path_allowed(path, allowed)
        and not _path_allowed(path, (".lab_automation",))
    ]


def _ensure_minimum_artifacts(result_dir: Path, *, dry_run: bool) -> dict[str, str]:
    """Locate agent artifacts; synthesize clearly marked dry-run files only."""
    result_dir.mkdir(parents=True, exist_ok=True)
    placeholders = {
        "agent_report.md": "# DRY RUN placeholder\n\nNo executor was invoked.\n",
        "result.json": '{"dry_run_placeholder": true}\n',
        "data_gaps.json": '{"dry_run_placeholder": true}\n',
    }
    origins: dict[str, str] = {}
    for name, placeholder in placeholders.items():
        path = result_dir / name
        if path.is_file():
            origins[name] = "agent_generated"
        elif dry_run:
            path.write_text(placeholder, encoding="utf-8")
            origins[name] = "dry_run_placeholder"
        else:
            origins[name] = "missing"
    return origins


def _runner_hooks_dir() -> Path:
    """Return hooks shipped with the exact Lab Automation runner source."""
    hooks_dir = Path(__file__).resolve().parents[1] / "scripts" / "hooks"
    pre_commit = hooks_dir / "pre-commit"
    if not pre_commit.is_file():
        raise FileNotFoundError(
            f"runner pre-commit hook not found: {pre_commit}"
        )
    return hooks_dir


def _candidate_commit(worktree: Path, job_id: str, dry_run: bool) -> str | None:
    if dry_run:
        return None
    if not _changed_paths(worktree):
        return _current_sha(worktree)
    _git(worktree, "add", "--all")
    hooks_dir = _runner_hooks_dir()
    commit_args = (
        "-c",
        f"core.hooksPath={hooks_dir}",
        "commit",
        "-m",
        f"lab-automation: candidate result for {job_id}",
    )
    proc = _git(worktree, *commit_args, check=False)
    if proc.returncode != 0:
        raise CommandFailure(
            {
                "schema_version": "command-failure/0.1",
                "stage": "candidate_commit",
                "command": ["git", *commit_args],
                "cwd": str(worktree),
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }
        )
    return _current_sha(worktree)


def _store_file(
    store: LocalArtifactStore,
    path: Path,
    *,
    kind: str,
    retention_class: str,
    metadata: dict[str, Any] | None = None,
) -> ArtifactRef:
    return store.put_file(
        path,
        kind=kind,
        retention_class=retention_class,
        metadata=metadata,
    )


def _artifact_manifest_entry(
    ref: ArtifactRef,
    *,
    repo_path: str | None = None,
    origin: str | None = None,
) -> dict[str, Any]:
    payload = {
        "artifact_id": ref.artifact_id,
        "sha256": ref.sha256,
        "byte_size": ref.byte_size,
        "kind": ref.kind,
        "logical_uri": ref.logical_uri,
        "retention_class": ref.retention_class,
    }
    if repo_path is not None:
        payload["repo_path"] = repo_path
    if origin is not None:
        payload["origin"] = origin
    return payload


def execute_job(
    repo: Path,
    job_path: Path,
    worktree_root: Path,
    state_root: Path,
    dry_run: bool = True,
) -> int:
    job, raw = _read_job(job_path)
    if raw.get("execution_mode") is not None:
        from lab_automation.local_observation import execute
        return execute(repo, job_path, worktree_root, state_root, dry_run=dry_run)
    _validate_job(job)
    run_id = str(uuid4())
    candidate_branch = _candidate_branch(job.job_id, run_id)
    ledger_path = state_root / "ledger" / f"{job.job_id}.jsonl"
    ledger = AppendOnlyLedger(ledger_path)
    store = LocalArtifactStore(state_root / "artifacts")

    base_sha = _current_sha(repo, job.branch)
    worktree = _worktree_path(worktree_root, job.job_id, run_id)
    candidate_sha: str | None = None
    artifact_entries: list[dict[str, Any]] = []
    logical_artifact_refs: list[str] = []
    run_succeeded = False

    ledger.append(
        RunEvent(
            job_id=job.job_id,
            run_id=run_id,
            stage="intake",
            status="started",
            actor="local_runner",
            runner_version=RUNNER_VERSION,
            base_sha=base_sha,
            authority_refs=job.authority_refs,
            metadata={
                "job_path": str(job_path),
                "dry_run": dry_run,
                "candidate_branch": candidate_branch,
            },
        )
    )

    try:
        if not dry_run:
            worktree.parent.mkdir(parents=True, exist_ok=True)
            _git(repo, "worktree", "add", "-b", candidate_branch, str(worktree), job.branch)
            result_dir = worktree / ".lab_automation" / "runs" / job.job_id / run_id
        else:
            worktree = repo
            result_dir = state_root / "dry_runs" / job.job_id / run_id

        authority_paths = _authority_snapshot(
            worktree,
            job.authority_refs,
            result_dir / "authority_snapshot",
        )
        authority_logical_refs: list[str] = []
        for ref_name, path in zip(job.authority_refs, authority_paths):
            artifact_ref = _store_file(
                store,
                path,
                kind="authority_snapshot",
                retention_class="irreplaceable",
                metadata={"authority_ref": ref_name, "run_id": run_id},
            )
            authority_logical_refs.append(artifact_ref.logical_uri)
            logical_artifact_refs.append(artifact_ref.logical_uri)
            repo_path = None if dry_run else str(path.relative_to(worktree))
            artifact_entries.append(
                _artifact_manifest_entry(
                    artifact_ref,
                    repo_path=repo_path,
                    origin="runner_snapshot",
                )
            )
        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="authority_load",
                status="completed",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                authority_refs=job.authority_refs,
                artifact_refs=tuple(authority_logical_refs),
            )
        )

        prompt = _build_codex_prompt(job, result_dir)
        prompt_ref = store.put_text(
            prompt,
            kind="agent_prompt",
            retention_class="irreplaceable",
            metadata={"job_id": job.job_id, "run_id": run_id},
        )
        input_snapshot = {
            "schema_version": "agent-input-snapshot/0.1",
            "job": asdict(job),
            "raw_job": raw,
            "base_sha": base_sha,
            "authority_artifact_refs": authority_logical_refs,
            "prompt_ref": prompt_ref.logical_uri,
            "runner_version": RUNNER_VERSION,
        }
        input_snapshot_ref = store.put_json(
            input_snapshot,
            kind="agent_input_snapshot",
            retention_class="irreplaceable",
            metadata={"job_id": job.job_id, "run_id": run_id},
        )
        for ref in (prompt_ref, input_snapshot_ref):
            logical_artifact_refs.append(ref.logical_uri)
            artifact_entries.append(_artifact_manifest_entry(ref, origin="runner_generated"))

        invocation_id = str(uuid4())
        started_at = _utc_now()
        codex_result = _invoke_codex(
            worktree,
            job,
            raw,
            prompt,
            dry_run=dry_run,
        )
        ended_at = _utc_now()
        raw_output_ref = store.put_json(
            codex_result,
            kind="raw_invocation_result",
            retention_class="irreplaceable",
            metadata={"job_id": job.job_id, "run_id": run_id, "invocation_id": invocation_id},
        )
        invocation_record = InvocationRecord(
            run_id=run_id,
            actor="codex",
            backend="codex_cli",
            execution_intent="primary",
            invocation_id=invocation_id,
            input_snapshot_ref=input_snapshot_ref.logical_uri,
            output_ref=raw_output_ref.logical_uri,
            requested_identity="codex_cli",
            identity_assurance="requested_only",
            started_at=started_at,
            ended_at=ended_at,
            status="completed" if codex_result["returncode"] == 0 else "failed",
            returncode=codex_result["returncode"],
            metadata={"command": codex_result["command"], "dry_run": dry_run},
        )
        invocation_record_ref = store.put_json(
            invocation_record.to_dict(),
            kind="invocation_record",
            retention_class="irreplaceable",
            metadata={"job_id": job.job_id, "run_id": run_id, "invocation_id": invocation_id},
        )
        for ref in (raw_output_ref, invocation_record_ref):
            logical_artifact_refs.append(ref.logical_uri)
            artifact_entries.append(_artifact_manifest_entry(ref, origin="runner_generated"))

        origins = _ensure_minimum_artifacts(result_dir, dry_run=dry_run)
        review_invocation = {
            "schema_version": "invocation-review/0.1",
            "invocation": invocation_record.to_dict(),
            "prompt_ref": prompt_ref.logical_uri,
            "input_snapshot_ref": input_snapshot_ref.logical_uri,
            "raw_output_ref": raw_output_ref.logical_uri,
            "invocation_record_ref": invocation_record_ref.logical_uri,
        }
        invocation_path = result_dir / "codex_invocation.json"
        invocation_path.write_text(
            json.dumps(review_invocation, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        origins["codex_invocation.json"] = "runner_generated"

        result_refs: dict[str, ArtifactRef] = {}
        for name, kind in (
            ("agent_report.md", "agent_report"),
            ("result.json", "agent_result"),
            ("data_gaps.json", "data_gaps"),
            ("codex_invocation.json", "invocation_review"),
        ):
            path = result_dir / name
            if not path.is_file():
                continue
            retention = "irreplaceable" if name != "codex_invocation.json" else "reconstructable"
            ref = _store_file(
                store,
                path,
                kind=kind,
                retention_class=retention,
                metadata={"job_id": job.job_id, "run_id": run_id, "origin": origins[name]},
            )
            result_refs[name] = ref
            logical_artifact_refs.append(ref.logical_uri)
            repo_path = None if dry_run else str(path.relative_to(worktree))
            artifact_entries.append(
                _artifact_manifest_entry(ref, repo_path=repo_path, origin=origins[name])
            )

        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="agent_execution",
                status="completed" if codex_result["returncode"] == 0 else "failed",
                actor="codex",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                artifact_refs=tuple(
                    [
                        prompt_ref.logical_uri,
                        input_snapshot_ref.logical_uri,
                        raw_output_ref.logical_uri,
                        invocation_record_ref.logical_uri,
                    ]
                    + [ref.logical_uri for ref in result_refs.values()]
                ),
                invocation_ids=(invocation_id,),
                input_snapshot_ref=input_snapshot_ref.logical_uri,
                output_ref=raw_output_ref.logical_uri,
                error=codex_result.get("stderr") or None,
                metadata={
                    "returncode": codex_result["returncode"],
                    "command": codex_result["command"],
                    "execution_status": (
                        "succeeded" if codex_result["returncode"] == 0 else "failed"
                    ),
                },
            )
        )
        if codex_result["returncode"] != 0:
            raise RuntimeError("Codex execution failed")

        output_findings = [
            require_output_contract(
                origins,
                required_names=REQUIRED_AGENT_ARTIFACTS,
            )
        ]
        if origins["agent_report.md"] == "agent_generated":
            output_findings.append(
                validate_nonempty_text_artifact(result_dir / "agent_report.md")
            )
        if origins["result.json"] == "agent_generated":
            output_findings.append(
                validate_json_artifact(
                    result_dir / "result.json",
                    reject_empty_object=True,
                )
            )
        if origins["data_gaps.json"] == "agent_generated":
            output_findings.append(
                validate_json_artifact(result_dir / "data_gaps.json")
            )
        output_failures = [
            finding for finding in output_findings if finding.status != "PASS"
        ]
        missing_artifacts = [
            name
            for name in REQUIRED_AGENT_ARTIFACTS
            if origins[name] != "agent_generated"
        ]
        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="output_contract",
                status=(
                    "dry_run_only"
                    if dry_run
                    else ("failed" if output_failures else "completed")
                ),
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                artifact_refs=tuple(ref.logical_uri for ref in result_refs.values()),
                metadata={
                    "dry_run": dry_run,
                    "findings": [asdict(finding) for finding in output_findings],
                    "missing_artifacts": missing_artifacts,
                    "origins": origins,
                },
            )
        )
        if not dry_run and output_failures:
            raise RuntimeError(
                "; ".join(finding.message for finding in output_failures)
            )

        executor_paths = [] if dry_run else _changed_paths(worktree)
        meaningful_paths: list[str] = []
        if not dry_run:
            _enforce_write_scope(
                executor_paths,
                job.allowed_write_paths + (".lab_automation",),
            )
            meaningful_paths = _meaningful_changed_paths(
                executor_paths,
                job.allowed_write_paths,
            )
            ledger.append(
                RunEvent(
                    job_id=job.job_id,
                    run_id=run_id,
                    stage="workload_change",
                    status="completed" if meaningful_paths else "failed",
                    actor="local_runner",
                    runner_version=RUNNER_VERSION,
                    base_sha=base_sha,
                    metadata={
                        "changed_paths": executor_paths,
                        "meaningful_changed_paths": meaningful_paths,
                    },
                )
            )
            if not meaningful_paths:
                raise RuntimeError(
                    "real run produced no meaningful changed path within the "
                    "Job's allowed write scope"
                )

        test_results = _run_tests(worktree, raw, dry_run=dry_run)
        tests_path = result_dir / "tests.json"
        tests_path.write_text(
            json.dumps(test_results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tests_ref = _store_file(
            store,
            tests_path,
            kind="test_results",
            retention_class="irreplaceable",
            metadata={"job_id": job.job_id, "run_id": run_id},
        )
        logical_artifact_refs.append(tests_ref.logical_uri)
        artifact_entries.append(
            _artifact_manifest_entry(
                tests_ref,
                repo_path=None if dry_run else str(tests_path.relative_to(worktree)),
                origin="runner_generated",
            )
        )
        failing = [row for row in test_results if row.get("returncode") != 0]
        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="tests",
                status="failed" if failing else "completed",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                artifact_refs=(tests_ref.logical_uri,),
                test_summary=f"{len(test_results)} commands; {len(failing)} failed",
            )
        )
        if failing:
            raise RuntimeError("One or more test commands failed")

        paths_before_manifest = [] if dry_run else _changed_paths(worktree)
        if not dry_run:
            _enforce_write_scope(
                paths_before_manifest,
                job.allowed_write_paths + (".lab_automation",),
            )

        manifest = {
            "schema_version": "run-manifest/0.2",
            "job": asdict(job),
            "run_id": run_id,
            "runner_version": RUNNER_VERSION,
            "base_sha": base_sha,
            "candidate_branch": candidate_branch if not dry_run else None,
            "changed_paths_before_manifest": paths_before_manifest,
            "meaningful_changed_paths": meaningful_paths,
            "artifacts": artifact_entries,
            "promotion_state": (
                "dry_run_complete" if dry_run else "waiting_for_push_approval"
            ),
            "push_performed": False,
            "merge_performed": False,
            "deploy_performed": False,
            "candidate_sha_canonical_home": "external_append_only_run_ledger",
        }
        manifest_path = result_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        manifest_ref = _store_file(
            store,
            manifest_path,
            kind="run_manifest",
            retention_class="irreplaceable",
            metadata={"job_id": job.job_id, "run_id": run_id},
        )
        logical_artifact_refs.append(manifest_ref.logical_uri)

        if not dry_run:
            paths = _changed_paths(worktree)
            _enforce_write_scope(paths, job.allowed_write_paths + (".lab_automation",))
            candidate_sha = _candidate_commit(worktree, job.job_id, dry_run=False)
            terminal_status = "waiting_for_push_approval"
        else:
            paths = []
            terminal_status = "dry_run_complete"

        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="candidate_revision",
                status=terminal_status,
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                candidate_sha=candidate_sha,
                authority_refs=job.authority_refs,
                artifact_refs=tuple(logical_artifact_refs),
                invocation_ids=(invocation_id,),
                input_snapshot_ref=input_snapshot_ref.logical_uri,
                output_ref=result_refs["result.json"].logical_uri,
                metadata={
                    "candidate_branch": candidate_branch if not dry_run else None,
                    "manifest_ref": manifest_ref.logical_uri,
                    "push_performed": False,
                    "merge_performed": False,
                    "deploy_performed": False,
                    "changed_paths": paths,
                },
            )
        )
        run_succeeded = True
        return 0
    except Exception as exc:
        failure_artifact_ref: str | None = None
        if isinstance(exc, CommandFailure):
            failure_ref = store.put_json(
                {
                    **exc.payload,
                    "job_id": job.job_id,
                    "run_id": run_id,
                },
                kind="command_failure",
                retention_class="irreplaceable",
                metadata={
                    "job_id": job.job_id,
                    "run_id": run_id,
                    "stage": exc.payload["stage"],
                },
            )
            failure_artifact_ref = failure_ref.logical_uri
            logical_artifact_refs.append(failure_artifact_ref)
        preserved_worktree_path = (
            str(worktree)
            if not dry_run and worktree != repo and worktree.is_dir()
            else None
        )
        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="terminal",
                status="failed",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                candidate_sha=candidate_sha,
                artifact_refs=tuple(logical_artifact_refs),
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "failure_artifact_ref": failure_artifact_ref,
                    "preserved_worktree_path": preserved_worktree_path,
                },
            )
        )
        print(f"runner failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if run_succeeded and not dry_run and worktree != repo and worktree.exists():
            _git(repo, "worktree", "remove", "--force", str(worktree), check=False)



def recover_candidate_commit(
    repo: Path,
    job_path: Path,
    state_root: Path,
    run_id: str,
) -> int:
    """Recover only a preserved candidate_commit failure.

    Recovery deliberately does not re-run Codex or create a new Run ID/worktree.
    It revalidates the preserved candidate, re-runs the Job test contract, then
    commits with the hook version pinned to the current Lab Automation runner.
    """

    job, raw = _read_job(job_path)
    _validate_job(job)

    ledger_path = state_root / "ledger" / f"{job.job_id}.jsonl"
    ledger = AppendOnlyLedger(ledger_path)
    store = LocalArtifactStore(state_root / "artifacts")

    events = [
        row
        for row in ledger.read_all()
        if row.get("run_id") == run_id
    ]

    if not events:
        print(
            f"recovery failed: run_id not found for job {job.job_id}: {run_id}",
            file=sys.stderr,
        )
        return 1

    terminal = next(
        (
            row
            for row in reversed(events)
            if row.get("stage") == "terminal"
            and row.get("status") == "failed"
        ),
        None,
    )

    if terminal is None:
        print(
            f"recovery failed: no failed terminal event for run {run_id}",
            file=sys.stderr,
        )
        return 1

    terminal_event_id = terminal.get("event_id")
    base_sha = terminal.get("base_sha")
    failure_artifact_ref = (
        terminal.get("metadata", {}).get("failure_artifact_ref")
    )
    preserved_worktree_raw = (
        terminal.get("metadata", {}).get("preserved_worktree_path")
    )

    recovery_artifact_refs: list[str] = []

    try:
        if terminal.get("job_id") != job.job_id:
            raise ValueError(
                "recovery job_id does not match failed run"
            )

        if not failure_artifact_ref:
            raise ValueError(
                "failed terminal event has no failure_artifact_ref"
            )

        failure = json.loads(
            store.read_bytes(failure_artifact_ref)
        )

        if failure.get("job_id") != job.job_id:
            raise ValueError(
                "failure artifact job_id does not match Job"
            )

        if failure.get("run_id") != run_id:
            raise ValueError(
                "failure artifact run_id does not match requested run"
            )

        if failure.get("stage") != "candidate_commit":
            raise ValueError(
                "v0.1 recovery supports candidate_commit failures only"
            )

        if not preserved_worktree_raw:
            raise ValueError(
                "failed run has no preserved_worktree_path"
            )

        worktree = Path(preserved_worktree_raw).expanduser().resolve()

        if not worktree.is_dir():
            raise FileNotFoundError(
                f"preserved worktree not found: {worktree}"
            )

        failure_cwd = failure.get("cwd")
        if failure_cwd and Path(failure_cwd).expanduser().resolve() != worktree:
            raise ValueError(
                "failure artifact cwd does not match preserved worktree"
            )

        expected_branch = _candidate_branch(job.job_id, run_id)
        current_branch = _git(
            worktree,
            "branch",
            "--show-current",
        ).stdout.strip()

        if current_branch != expected_branch:
            raise ValueError(
                f"candidate branch mismatch: expected {expected_branch}, "
                f"found {current_branch}"
            )

        if not base_sha:
            raise ValueError("failed run has no recorded base_sha")

        current_head = _current_sha(worktree)
        if current_head != base_sha:
            raise ValueError(
                f"preserved worktree HEAD mismatch: expected {base_sha}, "
                f"found {current_head}"
            )

        changed_paths = _changed_paths(worktree)
        if not changed_paths:
            raise ValueError(
                "preserved worktree has no candidate changes to recover"
            )

        _enforce_write_scope(
            changed_paths,
            job.allowed_write_paths + (".lab_automation",),
        )

        meaningful_paths = _meaningful_changed_paths(
            changed_paths,
            job.allowed_write_paths,
        )
        if not meaningful_paths:
            raise ValueError(
                "preserved worktree has no meaningful changed path "
                "within the Job write scope"
            )

        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="recovery",
                status="started",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                metadata={
                    "recovery_kind": "candidate_commit_only",
                    "recovery_of_event_id": terminal_event_id,
                    "preserved_worktree_path": str(worktree),
                    "candidate_branch": expected_branch,
                    "changed_paths": changed_paths,
                    "meaningful_changed_paths": meaningful_paths,
                    "codex_reinvoked": False,
                },
            )
        )

        # Re-run the exact Job test contract. Do not re-run Codex.
        test_results = _run_tests(
            worktree,
            raw,
            dry_run=False,
        )

        recovery_tests_ref = store.put_json(
            {
                "schema_version": "recovery-test-results/0.1",
                "job_id": job.job_id,
                "run_id": run_id,
                "runner_version": RUNNER_VERSION,
                "recovery_of_event_id": terminal_event_id,
                "test_results": test_results,
            },
            kind="recovery_test_results",
            retention_class="irreplaceable",
            metadata={
                "job_id": job.job_id,
                "run_id": run_id,
                "recovery_of_event_id": terminal_event_id,
            },
        )
        recovery_artifact_refs.append(
            recovery_tests_ref.logical_uri
        )

        failing = [
            row
            for row in test_results
            if row.get("returncode") != 0
        ]

        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="recovery_tests",
                status="failed" if failing else "completed",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                artifact_refs=(
                    recovery_tests_ref.logical_uri,
                ),
                test_summary=(
                    f"{len(test_results)} commands; "
                    f"{len(failing)} failed"
                ),
                metadata={
                    "recovery_of_event_id": terminal_event_id,
                    "codex_reinvoked": False,
                },
            )
        )

        if failing:
            raise RuntimeError(
                "One or more recovery test commands failed"
            )

        # Tests should not have expanded the write scope.
        post_test_paths = _changed_paths(worktree)
        _enforce_write_scope(
            post_test_paths,
            job.allowed_write_paths + (".lab_automation",),
        )

        post_test_meaningful = _meaningful_changed_paths(
            post_test_paths,
            job.allowed_write_paths,
        )
        if not post_test_meaningful:
            raise ValueError(
                "candidate changes disappeared before recovery commit"
            )

        candidate_sha = _candidate_commit(
            worktree,
            job.job_id,
            dry_run=False,
        )

        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="candidate_revision",
                status="waiting_for_push_approval",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                candidate_sha=candidate_sha,
                authority_refs=job.authority_refs,
                artifact_refs=tuple(
                    recovery_artifact_refs
                ),
                test_summary=(
                    f"{len(test_results)} recovery commands; "
                    "0 failed"
                ),
                metadata={
                    "candidate_branch": expected_branch,
                    "recovery_of_run_id": run_id,
                    "recovery_of_event_id": terminal_event_id,
                    "preserved_worktree_path": str(worktree),
                    "changed_paths": post_test_paths,
                    "meaningful_changed_paths": post_test_meaningful,
                    "push_performed": False,
                    "merge_performed": False,
                    "deploy_performed": False,
                    "codex_reinvoked": False,
                },
                supersedes_event_id=terminal_event_id,
            )
        )

        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="recovery",
                status="completed",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                candidate_sha=candidate_sha,
                artifact_refs=tuple(
                    recovery_artifact_refs
                ),
                metadata={
                    "recovery_kind": "candidate_commit_only",
                    "recovery_of_event_id": terminal_event_id,
                    "candidate_branch": expected_branch,
                    "push_performed": False,
                    "merge_performed": False,
                    "deploy_performed": False,
                    "codex_reinvoked": False,
                },
                supersedes_event_id=terminal_event_id,
            )
        )

        # Same lifecycle as a successful normal run:
        # candidate branch/commit remain; temporary worktree is removed.
        _git(
            repo,
            "worktree",
            "remove",
            "--force",
            str(worktree),
            check=False,
        )

        print(
            f"recovered run {run_id}: candidate {candidate_sha} "
            "is waiting_for_push_approval"
        )
        return 0

    except Exception as exc:
        failure_ref: str | None = None

        if isinstance(exc, CommandFailure):
            recovery_failure_ref = store.put_json(
                {
                    **exc.payload,
                    "job_id": job.job_id,
                    "run_id": run_id,
                    "recovery_of_event_id": terminal_event_id,
                },
                kind="command_failure",
                retention_class="irreplaceable",
                metadata={
                    "job_id": job.job_id,
                    "run_id": run_id,
                    "stage": exc.payload["stage"],
                    "recovery": True,
                },
            )
            failure_ref = recovery_failure_ref.logical_uri
            recovery_artifact_refs.append(failure_ref)

        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="recovery",
                status="failed",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                artifact_refs=tuple(
                    recovery_artifact_refs
                ),
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "recovery_kind": "candidate_commit_only",
                    "recovery_of_event_id": terminal_event_id,
                    "failure_artifact_ref": failure_ref,
                    "preserved_worktree_path": preserved_worktree_raw,
                    "codex_reinvoked": False,
                },
            )
        )

        print(
            f"recovery failed: {exc}",
            file=sys.stderr,
        )
        return 1

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=Path(tempfile.gettempdir()) / "stockvis-lab-worktrees",
    )
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path.home() / ".stockvis-lab-automation",
        help=(
            "External append-only runtime state and content-addressed artifacts; "
            "kept outside the repo checkout."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run Codex and git mutations. Default is dry-run.",
    )
    parser.add_argument(
        "--recover-run",
        metavar="RUN_ID",
        help=(
            "Recover a preserved candidate_commit failure without re-running "
            "Codex. Requires --execute."
        ),
    )
    args = parser.parse_args()

    if args.recover_run:
        if not args.execute:
            parser.error("--recover-run requires --execute")
        return recover_candidate_commit(
            repo=args.repo.resolve(),
            job_path=args.job.resolve(),
            state_root=args.state_root.expanduser().resolve(),
            run_id=args.recover_run,
        )

    return execute_job(
        repo=args.repo.resolve(),
        job_path=args.job.resolve(),
        worktree_root=args.worktree_root.resolve(),
        state_root=args.state_root.expanduser().resolve(),
        dry_run=not args.execute,
    )


if __name__ == "__main__":
    raise SystemExit(main())
