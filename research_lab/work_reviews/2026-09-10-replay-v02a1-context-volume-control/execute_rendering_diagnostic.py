#!/usr/bin/env python3
"""Run one bounded offline diagnostic and commit evidence locally without push."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BRANCH = "feature/research-replay-v02a1-context-volume-control"
CORRECTION = ROOT / "acquisition_runs/official-pinned-001/continuations/jinja2-pinned-001"
OUTPUT = CORRECTION / "diagnostics/raw-rendering-and-token-accounting-001"
EXPERIMENTS = ROOT.parents[3] / ".experiments"
VENV = EXPERIMENTS / "replay-v02a1-jinja2-pinned-001/venv"
SNAPSHOT = EXPERIMENTS / "replay-v02a1-official-pinned-001/tokenizer_snapshot"


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_start() -> None:
    if git("branch", "--show-current", capture=True) != BRANCH:
        raise RuntimeError("wrong_branch")
    if subprocess.run(["git", "diff", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("tracked_worktree_changes_present")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("preexisting_staged_changes_present")
    if OUTPUT.exists():
        raise RuntimeError("diagnostic_lineage_already_exists")
    for required in (VENV / "bin/python", SNAPSHOT, CORRECTION / "GATE_SHA256SUMS"):
        if not required.exists():
            raise RuntimeError("required_existing_material_missing:" + required.name)


def main() -> int:
    verify_start()
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS_RAW_RENDERING_DIAGNOSTIC_PREP"],
        cwd=ROOT, check=True,
    )
    subprocess.run(
        ["shasum", "-a", "256", "-c", "GATE_SHA256SUMS"],
        cwd=CORRECTION, check=True,
    )
    env = os.environ.copy()
    env.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_rendering_diagnostic"],
        cwd=ROOT, env=env, check=True,
    )
    result_path = OUTPUT / "diagnostic_result.json"
    subprocess.run([
        str(VENV / "bin/python"), str(ROOT / "rendering_diagnostic.py"),
        "--snapshot", str(SNAPSHOT),
        "--source-root", str(ROOT / "source_snapshot"),
        "--output", str(result_path),
    ], cwd=ROOT, env=env, check=True)
    result = json.loads(result_path.read_text())
    execution = {
        "status": "completed_no_network_no_model_diagnostic",
        "outcome": result["outcome"],
        "network_attempts": 0,
        "model_provider_invocations": 0,
        "fixed_experimental_arms_generated": 0,
        "historical_artifacts_modified": False,
        "publication_performed": False,
    }
    execution_path = OUTPUT / "execution_record.json"
    execution_path.write_text(json.dumps(execution, indent=2, sort_keys=True) + "\n")
    files = [result_path, execution_path]
    (OUTPUT / "SHA256SUMS").write_text("".join(
        f"{sha(path)}  {path.name}\n" for path in files
    ))
    git("add", str(OUTPUT.relative_to(REPO)))
    staged = git("diff", "--cached", "--name-status", capture=True).splitlines()
    prefix = str(OUTPUT.relative_to(REPO)) + "/"
    if not staged or any(
        line.split("\t", 1)[0] != "A" or not line.split("\t", 1)[1].startswith(prefix)
        for line in staged
    ):
        raise RuntimeError("append_only_staged_scope_violation")
    git("commit", "-m", "[skip ci] Record v0.2A.1 offline rendering diagnostic")
    print("STATUS=" + execution["status"])
    print("OUTCOME=" + result["outcome"])
    print("MODEL_PROVIDER_INVOCATIONS=0")
    print("NETWORK_ATTEMPTS=0")
    print("LOCAL_COMMIT=" + git("rev-parse", "HEAD", capture=True))
    print("RESULT_PATH=" + str(OUTPUT))
    print("PUSH_PERFORMED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
