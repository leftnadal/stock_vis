#!/usr/bin/env python3
"""Run the fixed v0.2A experiment once, verify artifacts, and push its review commit."""
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
BRANCH = "feature/research-replay-v02a-summary-target"


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        args, cwd=REPO, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_token() -> str:
    token = os.environ.get("DEEPINFRA_TOKEN") or os.environ.get("DEEP_INFRA_API_KEY")
    if not token:
        token = provider.token_from_file(ROOT.parents[3] / ".env")
    return provider.valid_token(token or "")


def main() -> int:
    if run("git", "branch", "--show-current", capture=True) != BRANCH:
        raise RuntimeError("wrong_branch")
    if run("git", "status", "--porcelain", capture=True):
        raise RuntimeError("worktree_not_clean")
    if (ROOT / "executions").exists():
        raise RuntimeError("executions_already_exist_refusing_duplicate_run")

    token = load_token()
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=ROOT, check=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_replay", "test_completion_contract"],
        cwd=ROOT, env=env, check=True,
    )
    subprocess.run([sys.executable, "replay.py"], cwd=ROOT, env=env, check=True)

    batches = [path for path in (ROOT / "executions").iterdir() if path.is_dir()]
    if len(batches) != 1:
        raise RuntimeError("expected_exactly_one_execution_batch")
    batch = batches[0]
    files = sorted(path for path in batch.rglob("*") if path.is_file())
    token_bytes = token.encode()
    for path in files:
        data = path.read_bytes()
        if token_bytes in data or b"Authorization: Bearer" in data:
            raise RuntimeError("credential_material_detected_refusing_publish")

    records = [{"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size}
               for path in files]
    artifact_manifest = {
        "batch_id": batch.name,
        "historical_artifacts_modified": False,
        "credential_material_check": "passed",
        "files": records,
    }
    (batch / "ARTIFACT_MANIFEST.json").write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    checksums = sorted(path for path in batch.rglob("*") if path.is_file())
    (batch / "SHA256SUMS").write_text(
        "".join(f"{sha(path)}  {path.relative_to(batch)}\n" for path in checksums)
    )

    run("git", "add", str(batch.relative_to(REPO)))
    staged = run("git", "diff", "--cached", "--name-only", capture=True).splitlines()
    prefix = str(ROOT.relative_to(REPO)) + "/executions/"
    if not staged or any(not path.startswith(prefix) for path in staged):
        raise RuntimeError("staged_scope_violation")
    run("git", "commit", "-m", "[skip ci] Add Replay v0.2A execution evidence")
    run("git", "push", "origin", f"HEAD:{BRANCH}")
    print("PUBLISHED_COMMIT=" + run("git", "rev-parse", "HEAD", capture=True))
    print("RESULT_PATH=" + str(batch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
