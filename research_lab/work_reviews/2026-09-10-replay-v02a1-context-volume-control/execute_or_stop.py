#!/usr/bin/env python3
"""Publish tokenizer preflight, then execute only when the strict gate passes."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import provider_adapter as provider

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BRANCH = "feature/research-replay-v02a1-context-volume-control"


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_start():
    if git("branch", "--show-current", capture=True) != BRANCH:
        raise RuntimeError("wrong_branch")
    if subprocess.run(["git", "diff", "--quiet"], cwd=REPO).returncode != 0:
        raise RuntimeError("tracked_worktree_changes_present")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode != 0:
        raise RuntimeError("preexisting_staged_changes_present")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", str(ROOT.relative_to(REPO))],
        cwd=REPO, check=True, text=True, stdout=subprocess.PIPE,
    ).stdout.strip()
    if status:
        raise RuntimeError("task_directory_not_clean")


def verify_staged(prefixes: tuple[str, ...]):
    staged = git("diff", "--cached", "--name-only", capture=True).splitlines()
    root_prefix = str(ROOT.relative_to(REPO)) + "/"
    if not staged or any(not path.startswith(root_prefix + prefixes) for path in staged):
        raise RuntimeError("staged_scope_violation")


def load_token() -> str:
    token = os.environ.get("DEEPINFRA_TOKEN") or os.environ.get("DEEP_INFRA_API_KEY")
    if not token:
        token = provider.token_from_file(ROOT.parents[3] / ".env")
    return provider.valid_token(token or "")


def publish_preflight():
    generated = ["preflight_result.json"]
    if json.loads((ROOT / "preflight_result.json").read_text())["status"] == "ready_for_fixed_execution":
        generated += ["plan.json", "visible"]
    git("add", *[str((ROOT / path).relative_to(REPO)) for path in generated])
    verify_staged(tuple(path + ("/" if path == "visible" else "") for path in generated))
    git("commit", "-m", "[skip ci] Record Replay v0.2A.1 tokenizer preflight")
    git("push", "origin", f"HEAD:{BRANCH}")


def publish_execution(token: str, execution_returncode: int):
    executions = ROOT / "executions"
    if not executions.exists():
        (ROOT / "execution_launch_failure.json").write_text(json.dumps({
            "status": "systemic_execution_error_before_batch_creation",
            "returncode": execution_returncode,
            "model_invocations": "unverified",
        }, indent=2) + "\n")
        paths = [ROOT / "execution_launch_failure.json"]
    else:
        batches = [path for path in executions.iterdir() if path.is_dir()]
        if len(batches) != 1:
            raise RuntimeError("expected_exactly_one_execution_batch")
        batch = batches[0]
        files = sorted(path for path in batch.rglob("*") if path.is_file())
        token_bytes = token.encode()
        for path in files:
            data = path.read_bytes()
            if token_bytes in data or b"Authorization: Bearer" in data:
                raise RuntimeError("credential_material_detected_refusing_publish")
        manifest = {
            "batch_id": batch.name,
            "credential_material_check": "passed",
            "historical_artifacts_modified": False,
            "execution_returncode": execution_returncode,
            "files": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size}
                      for path in files],
        }
        (batch / "ARTIFACT_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        checksums = sorted(path for path in batch.rglob("*") if path.is_file())
        (batch / "SHA256SUMS").write_text(
            "".join(f"{sha(path)}  {path.relative_to(batch)}\n" for path in checksums)
        )
        paths = [batch]
    git("add", *[str(path.relative_to(REPO)) for path in paths])
    verify_staged(tuple("executions/" if path.name != "execution_launch_failure.json" else "execution_launch_failure.json" for path in paths))
    git("commit", "-m", "[skip ci] Add Replay v0.2A.1 execution evidence")
    git("push", "origin", f"HEAD:{BRANCH}")


def main() -> int:
    verify_start()
    if (ROOT / "executions").exists() or (ROOT / "preflight_result.json").exists():
        raise RuntimeError("prior_run_artifact_exists_refusing_duplicate")
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=ROOT, check=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, "-m", "unittest", "-v", "test_preflight", "test_completion_contract"], cwd=ROOT, env=env, check=True)
    preflight = subprocess.run([sys.executable, "preflight.py"], cwd=ROOT, env=env)
    result = json.loads((ROOT / "preflight_result.json").read_text())
    publish_preflight()
    if result["status"] != "ready_for_fixed_execution":
        print("STATUS=blocked_before_model_invocation")
        print("BLOCKER=" + result["blocker"])
        print("PUBLISHED_COMMIT=" + git("rev-parse", "HEAD", capture=True))
        return 0
    if preflight.returncode != 0:
        raise RuntimeError("preflight_status_returncode_mismatch")

    token = load_token()
    execution = subprocess.run([sys.executable, "replay.py"], cwd=ROOT, env=env)
    publish_execution(token, execution.returncode)
    print("STATUS=" + ("execution_finished" if execution.returncode == 0 else "systemic_execution_error"))
    print("PUBLISHED_COMMIT=" + git("rev-parse", "HEAD", capture=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
