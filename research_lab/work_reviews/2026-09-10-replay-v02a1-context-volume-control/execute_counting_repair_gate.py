#!/usr/bin/env python3
"""Run and locally commit one counting-only historical exact-count gate."""
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
DIAGNOSTIC = CORRECTION / "diagnostics/raw-rendering-and-token-accounting-001"
OUTPUT = CORRECTION / "counting-repair-gate-001"
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
        raise RuntimeError("counting_repair_gate_already_exists")
    for required in (
        VENV / "bin/python", SNAPSHOT, DIAGNOSTIC / "SHA256SUMS",
        CORRECTION / "correction_result.json",
    ):
        if not required.exists():
            raise RuntimeError("required_existing_evidence_missing:" + required.name)


def main() -> int:
    verify_start()
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS_COUNTING_REPAIR_GATE_PREP"],
        cwd=ROOT, check=True,
    )
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=DIAGNOSTIC, check=True)
    env = os.environ.copy()
    env.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_preflight",
         "test_counting_repair_gate", "test_completion_contract"],
        cwd=ROOT, env=env, check=True,
    )
    dependency = json.loads((CORRECTION / "correction_dependency_manifest.json").read_text())
    revision = json.loads(
        (ROOT / "acquisition_runs/official-pinned-001/tokenizer_asset_manifest.json").read_text()
    )["immutable_revision"]
    result_path = OUTPUT / "gate_result.json"
    completed = subprocess.run([
        str(VENV / "bin/python"), str(ROOT / "counting_repair_gate.py"),
        "--snapshot", str(SNAPSHOT),
        "--source-root", str(ROOT / "source_snapshot"),
        "--revision", revision,
        "--output", str(result_path),
    ], cwd=ROOT, env=env)
    result = json.loads(result_path.read_text())
    record = {
        "status": result["status"],
        "gate_returncode": completed.returncode,
        "prior_diagnostic_commit": "e0749bca62e594f98910e172a561a4a012c99c88",
        "prior_diagnostic_outcome_label_preserved": "B_historical_string_body_not_fully_rendered",
        "interpretation_correction": "actual input_ids counts establish counting implementation defect",
        "corrected_environment_manifest_sha256": sha(CORRECTION / "correction_dependency_manifest.json"),
        "corrected_environment_status": dependency["status"],
        "network_attempts": 0,
        "provider_model_invocations": 0,
        "model_visible_arms_generated": 0,
        "historical_artifacts_modified": False,
        "push_performed": False,
    }
    record_path = OUTPUT / "execution_record.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    files = [result_path, record_path]
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
    git("commit", "-m", "[skip ci] Record v0.2A.1 counting-only exact gate")
    print("STATUS=" + result["status"])
    print("MODEL_VISIBLE_ARMS_GENERATED=0")
    print("PROVIDER_MODEL_INVOCATIONS=0")
    print("LOCAL_COMMIT=" + git("rev-parse", "HEAD", capture=True))
    print("RESULT_PATH=" + str(OUTPUT))
    print("PUSH_PERFORMED=false")
    return 0 if result["status"] == "exact_count_gate_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
