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
from lab_automation.integrity import require_output_contract
from lab_automation.ledger import AppendOnlyLedger, RunEvent

RUNNER_VERSION = "0.1.2"


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
- Do not push, merge, deploy, force-push, or modify main/master.
- DB access policy: {job.db_access}.
- Network policy: {job.network_policy}.
- Do not perform destructive actions.
- Record failures and uncertainty; do not hide unsuccessful attempts.
- Write a concise execution report to: {result_dir / 'agent_report.md'}
- Write machine-readable findings to: {result_dir / 'result.json'}
- If data gaps are found, write: {result_dir / 'data_gaps.json'}
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
    proc = _git(worktree, "status", "--porcelain")
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


def _ensure_minimum_artifacts(result_dir: Path) -> dict[str, str]:
    """Ensure review files exist while preserving whether the agent made them."""
    result_dir.mkdir(parents=True, exist_ok=True)
    origins: dict[str, str] = {}
    defaults = {
        "agent_report.md": "# Agent report\n\nNo report was produced by the agent.\n",
        "result.json": "{}\n",
        "data_gaps.json": "[]\n",
    }
    for name, default in defaults.items():
        path = result_dir / name
        if path.exists():
            origins[name] = "agent_generated"
        else:
            path.write_text(default, encoding="utf-8")
            origins[name] = "runner_placeholder"
    return origins


def _candidate_commit(worktree: Path, job_id: str, dry_run: bool) -> str | None:
    if dry_run:
        return None
    if not _changed_paths(worktree):
        return _current_sha(worktree)
    _git(worktree, "add", "--all")
    _git(worktree, "commit", "-m", f"lab-automation: candidate result for {job_id}")
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

        origins = _ensure_minimum_artifacts(result_dir)
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

        output_finding = require_output_contract(
            origins,
            required_names=("agent_report.md", "result.json"),
        )
        ledger.append(
            RunEvent(
                job_id=job.job_id,
                run_id=run_id,
                stage="output_contract",
                status="completed" if output_finding.status == "PASS" or dry_run else "failed",
                actor="local_runner",
                runner_version=RUNNER_VERSION,
                base_sha=base_sha,
                artifact_refs=tuple(ref.logical_uri for ref in result_refs.values()),
                metadata={
                    "integrity_code": output_finding.code,
                    "integrity_status": output_finding.status,
                    "message": output_finding.message,
                    "origins": origins,
                },
            )
        )
        if not dry_run and output_finding.status != "PASS":
            raise RuntimeError(output_finding.message)

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
        return 0
    except Exception as exc:
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
            )
        )
        print(f"runner failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if not dry_run and worktree != repo and worktree.exists():
            _git(repo, "worktree", "remove", "--force", str(worktree), check=False)


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
    args = parser.parse_args()
    return execute_job(
        repo=args.repo.resolve(),
        job_path=args.job.resolve(),
        worktree_root=args.worktree_root.resolve(),
        state_root=args.state_root.expanduser().resolve(),
        dry_run=not args.execute,
    )


if __name__ == "__main__":
    raise SystemExit(main())
