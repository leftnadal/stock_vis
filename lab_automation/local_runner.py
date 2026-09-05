"""Minimal MacBook Local Runner for StockVis Lab Automation Platform.

Scope v0.1:
- load one local JSON job file
- create an isolated git worktree from the declared branch
- record authority refs and base SHA
- invoke Codex CLI through a configurable command
- run declared test commands
- write structured result artifacts
- create a local candidate branch + commit
- stop in `waiting_for_push_approval`

It intentionally does NOT push, open/merge PRs, deploy, or mutate production DB.
Runtime ledger/state are stored outside the repository checkout by default so the
main Claude Code workspace is not dirtied by automation telemetry.
"""

from __future__ import annotations

from dataclasses import asdict
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

from lab_automation.contracts import JobEnvelope, JobStatus, Lab
from lab_automation.ledger import AppendOnlyLedger, RunEvent

RUNNER_VERSION = "0.1.1"


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


def _authority_snapshot(worktree: Path, refs: tuple[str, ...], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[str] = []
    for ref in refs:
        source = worktree / ref
        if not source.is_file():
            raise FileNotFoundError(f"authority ref not found: {ref}")
        target = output_dir / ref.replace("/", "__")
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        artifacts.append(str(target))
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
    result_dir: Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    command_template = raw.get("codex_command", ["codex", "exec", "-"])
    command = shlex.split(command_template) if isinstance(command_template, str) else list(command_template)
    prompt = _build_codex_prompt(job, result_dir)
    if dry_run:
        return {
            "command": command,
            "dry_run": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
            "prompt": prompt,
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


def _ensure_minimum_artifacts(result_dir: Path, codex_result: dict[str, Any]) -> None:
    result_dir.mkdir(parents=True, exist_ok=True)
    invocation_path = result_dir / "codex_invocation.json"
    invocation_path.write_text(
        json.dumps(codex_result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    if not (result_dir / "agent_report.md").exists():
        (result_dir / "agent_report.md").write_text(
            "# Agent report\n\nNo report was produced by the agent.\n",
            encoding="utf-8",
        )
    if not (result_dir / "result.json").exists():
        (result_dir / "result.json").write_text("{}\n", encoding="utf-8")
    if not (result_dir / "data_gaps.json").exists():
        (result_dir / "data_gaps.json").write_text("[]\n", encoding="utf-8")


def _candidate_commit(worktree: Path, job_id: str, dry_run: bool) -> str | None:
    if dry_run:
        return None
    if not _changed_paths(worktree):
        return _current_sha(worktree)
    _git(worktree, "add", "--all")
    _git(worktree, "commit", "-m", f"lab-automation: candidate result for {job_id}")
    return _current_sha(worktree)


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

    base_sha = _current_sha(repo, job.branch)
    worktree = _worktree_path(worktree_root, job.job_id, run_id)
    candidate_sha: str | None = None
    artifacts: list[str] = []

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
        else:
            worktree = repo

        result_dir = worktree / ".lab_automation" / "runs" / job.job_id / run_id
        authority_artifacts = _authority_snapshot(
            worktree,
            job.authority_refs,
            result_dir / "authority_snapshot",
        )
        artifacts.extend(authority_artifacts)
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
                artifact_refs=tuple(authority_artifacts),
            )
        )

        codex_result = _invoke_codex(worktree, job, raw, result_dir, dry_run=dry_run)
        _ensure_minimum_artifacts(result_dir, codex_result)
        artifacts.extend(
            str(path)
            for path in [
                result_dir / "agent_report.md",
                result_dir / "result.json",
                result_dir / "data_gaps.json",
                result_dir / "codex_invocation.json",
            ]
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
                artifact_refs=tuple(artifacts),
                error=codex_result.get("stderr") or None,
                metadata={
                    "returncode": codex_result["returncode"],
                    "command": codex_result["command"],
                },
            )
        )
        if codex_result["returncode"] != 0:
            raise RuntimeError("Codex execution failed")

        test_results = _run_tests(worktree, raw, dry_run=dry_run)
        tests_path = result_dir / "tests.json"
        tests_path.write_text(json.dumps(test_results, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(str(tests_path))
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
                artifact_refs=(str(tests_path),),
                test_summary=f"{len(test_results)} commands; {len(failing)} failed",
            )
        )
        if failing:
            raise RuntimeError("One or more test commands failed")

        paths = _changed_paths(worktree)
        _enforce_write_scope(paths, job.allowed_write_paths + (".lab_automation",))
        candidate_sha = _candidate_commit(worktree, job.job_id, dry_run=dry_run)

        manifest = {
            "job": asdict(job),
            "run_id": run_id,
            "runner_version": RUNNER_VERSION,
            "base_sha": base_sha,
            "candidate_branch": candidate_branch if not dry_run else None,
            "candidate_sha": candidate_sha,
            "changed_paths": paths,
            "artifacts": artifacts,
            "promotion_state": "waiting_for_push_approval",
            "push_performed": False,
            "merge_performed": False,
            "deploy_performed": False,
            "ledger_path": str(ledger_path),
        }
        manifest_path = result_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        if not dry_run:
            _git(worktree, "add", str(manifest_path.relative_to(worktree)))
            _git(worktree, "commit", "--amend", "--no-edit")
            candidate_sha = _current_sha(worktree)

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
                artifact_refs=tuple(artifacts + [str(manifest_path)]),
                metadata={
                    "candidate_branch": candidate_branch if not dry_run else None,
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
        help="External append-only runtime state; kept outside the repo checkout.",
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
