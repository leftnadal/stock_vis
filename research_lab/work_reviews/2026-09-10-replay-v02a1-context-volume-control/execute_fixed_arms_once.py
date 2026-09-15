#!/usr/bin/env python3
"""Seal preflight, execute two approved calls, and publish review evidence."""
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
CORRECTION = ROOT / "acquisition_runs/official-pinned-001/continuations/jinja2-pinned-001"
GATE = CORRECTION / "counting-repair-gate-001"
DIAGNOSTIC = CORRECTION / "diagnostics/raw-rendering-and-token-accounting-001"
FIXED = CORRECTION / "fixed-arms-001"
EXPERIMENTS = ROOT.parents[3] / ".experiments"
VENV = EXPERIMENTS / "replay-v02a1-jinja2-pinned-001/venv"
SNAPSHOT = EXPERIMENTS / "replay-v02a1-official-pinned-001/tokenizer_snapshot"


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(["git", *args], cwd=REPO, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_under(path: Path) -> list[Path]:
    return sorted(item for item in path.rglob("*") if item.is_file())


def write_checksums(path: Path, files: list[Path], base: Path):
    path.write_text("".join(f"{sha(item)}  {item.relative_to(base)}\n" for item in files))


def verify_start():
    if git("branch", "--show-current", capture=True) != BRANCH:
        raise RuntimeError("wrong_branch")
    if subprocess.run(["git", "diff", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("tracked_worktree_changes_present")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("preexisting_staged_changes_present")
    if FIXED.exists():
        raise RuntimeError("fixed_arm_lineage_already_exists")
    for required in (VENV / "bin/python", SNAPSHOT, GATE / "gate_result.json",
                     GATE / "SHA256SUMS", DIAGNOSTIC / "SHA256SUMS"):
        if not required.exists():
            raise RuntimeError("required_evidence_missing:" + required.name)


def verify_staged():
    lines = git("diff", "--cached", "--name-status", capture=True).splitlines()
    prefix = str(FIXED.relative_to(REPO)) + "/"
    if not lines or any(line.split("\t", 1)[0] != "A" or
                        not line.split("\t", 1)[1].startswith(prefix) for line in lines):
        raise RuntimeError("append_only_staged_scope_violation")


def publish(message: str) -> str:
    git("add", str(FIXED.relative_to(REPO)))
    verify_staged()
    git("commit", "-m", message)
    git("push", "origin", f"HEAD:{BRANCH}")
    return git("rev-parse", "HEAD", capture=True)


def load_token() -> str:
    token = os.environ.get("DEEPINFRA_TOKEN") or os.environ.get("DEEP_INFRA_API_KEY")
    if not token:
        token = provider.token_from_file(ROOT.parents[3] / ".env")
    return provider.valid_token(token or "")


def main() -> int:
    verify_start()
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS_FIXED_ARMS_PREP"],
                   cwd=ROOT, check=True)
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=GATE, check=True)
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=DIAGNOSTIC, check=True)
    env = os.environ.copy()
    env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    subprocess.run([sys.executable, "-m", "unittest", "-v", "test_preflight",
                    "test_build_fixed_arms", "test_replay_fixed_once",
                    "test_completion_contract"], cwd=ROOT, env=env, check=True)
    revision = json.loads(
        (ROOT / "acquisition_runs/official-pinned-001/tokenizer_asset_manifest.json").read_text()
    )["immutable_revision"]
    subprocess.run([
        str(VENV / "bin/python"), str(ROOT / "build_fixed_arms.py"),
        "--snapshot", str(SNAPSHOT), "--source-root", str(ROOT / "source_snapshot"),
        "--gate-result", str(GATE / "gate_result.json"), "--revision", revision,
        "--output", str(FIXED),
    ], cwd=ROOT, env=env, check=True)
    preflight = json.loads((FIXED / "preflight_result.json").read_text())
    if preflight["status"] != "ready_for_two_fixed_calls" or \
       preflight["long_control_input_tokens"] != 14387 or \
       preflight["provider_model_invocations"] != 0:
        raise RuntimeError("fixed_preflight_contract_failed")
    write_checksums(FIXED / "PRE_EXECUTION_SHA256SUMS", files_under(FIXED), FIXED)
    preflight_commit = publish("[skip ci] Seal v0.2A.1 fixed-arm inputs")

    token = load_token()
    run_env = env.copy()
    run_env["REPLAY_EXPERIMENT_ROOT"] = str(FIXED)
    completed = subprocess.run([str(VENV / "bin/python"), str(ROOT / "replay_fixed_once.py")],
                               cwd=ROOT, env=run_env)
    batches = [path for path in (FIXED / "executions").iterdir() if path.is_dir()]
    if len(batches) != 1:
        raise RuntimeError("expected_exactly_one_execution_batch")
    batch = batches[0]
    token_bytes = token.encode()
    for path in files_under(batch):
        data = path.read_bytes()
        if token_bytes in data or b"Authorization: Bearer" in data:
            raise RuntimeError("credential_material_detected")
    manifest = json.loads((batch / "manifest.json").read_text())
    record = {
        "status": manifest["status"], "execution_returncode": completed.returncode,
        "batch_id": batch.name, "preflight_commit": preflight_commit,
        "model_invocations": manifest["model_invocations"], "model_invocation_limit": 2,
        "retries": 0, "selective_rerun": False, "credential_material_check": "passed",
        "historical_artifacts_modified": False, "actual_cost_usd": None,
    }
    (FIXED / "execution_record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    execution_files = files_under(batch) + [FIXED / "execution_record.json"]
    write_checksums(FIXED / "EXECUTION_SHA256SUMS", execution_files, FIXED)
    commit = publish("[skip ci] Add v0.2A.1 fixed-arm execution evidence")
    print("STATUS=" + manifest["status"])
    print("MODEL_INVOCATIONS=" + str(manifest["model_invocations"]))
    print("PREFLIGHT_COMMIT=" + preflight_commit)
    print("PUBLISHED_COMMIT=" + commit)
    print("RESULT_PATH=" + str(batch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
