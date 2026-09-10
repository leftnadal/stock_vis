#!/usr/bin/env python3
"""Verify, execute, checksum, and publish the approved no-network diagnostic."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO = SCRIPT_ROOT.parents[2]
BRANCH = "feature/research-replay-v02a1-context-volume-control"
ACQUISITION = SCRIPT_ROOT / "acquisition_runs" / "official-pinned-001"
DIAGNOSTIC = ACQUISITION / "diagnostics" / "import-error-001"
EXTERNAL = SCRIPT_ROOT.parents[3] / ".experiments" / "replay-v02a1-official-pinned-001"


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


def verify_start() -> None:
    if git("branch", "--show-current", capture=True) != BRANCH:
        raise RuntimeError("wrong_branch")
    if subprocess.run(["git", "diff", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("tracked_worktree_changes_present")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("preexisting_staged_changes_present")
    if DIAGNOSTIC.exists():
        raise RuntimeError("diagnostic_already_exists_refusing_rerun")
    required = [
        EXTERNAL / "venv" / "bin" / "python",
        EXTERNAL / "tokenizer_snapshot",
        ACQUISITION / "tokenizer_asset_manifest.json",
        ACQUISITION / "dependency_manifest.json",
        ACQUISITION / "gate" / "preflight_result.json",
    ]
    if any(not path.exists() for path in required):
        raise RuntimeError("preserved_environment_or_evidence_missing")


def main() -> int:
    verify_start()
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS_DIAGNOSTIC_PREP"],
        cwd=SCRIPT_ROOT, check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_import_diagnostic"],
        cwd=SCRIPT_ROOT, check=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS"],
        cwd=ACQUISITION, check=True,
    )
    py = EXTERNAL / "venv" / "bin" / "python"
    output = DIAGNOSTIC / "diagnostic_result.json"
    env = {
        **os.environ,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "NO_PROXY": "*",
        "no_proxy": "*",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    subprocess.run([
        str(py), str(SCRIPT_ROOT / "diagnose_chat_template_import.py"),
        "--snapshot", str(EXTERNAL / "tokenizer_snapshot"),
        "--asset-manifest", str(ACQUISITION / "tokenizer_asset_manifest.json"),
        "--environment", str(EXTERNAL / "venv"),
        "--output", str(output),
    ], env=env, check=True)
    result = json.loads(output.read_text())
    record = {
        "status": result["status"],
        "network_attempt_count": result["network_attempt_count"],
        "package_installations": 0,
        "historical_count_gate_reruns": 0,
        "provider_or_model_invocations": 0,
        "historical_artifacts_modified": False,
    }
    (DIAGNOSTIC / "execution_record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    files = sorted(path for path in DIAGNOSTIC.iterdir() if path.is_file())
    (DIAGNOSTIC / "SHA256SUMS").write_text(
        "".join(f"{sha(path)}  {path.name}\n" for path in files)
    )
    token_markers = (b"Authorization: Bearer", b"DEEPINFRA_TOKEN", b"DEEP_INFRA_API_KEY")
    for path in DIAGNOSTIC.iterdir():
        if path.is_file() and any(marker in path.read_bytes() for marker in token_markers):
            raise RuntimeError("credential_marker_detected")
    git("add", str(DIAGNOSTIC.relative_to(REPO)))
    staged = git("diff", "--cached", "--name-only", capture=True).splitlines()
    prefix = str(DIAGNOSTIC.relative_to(REPO)) + "/"
    if not staged or any(not path.startswith(prefix) for path in staged):
        raise RuntimeError("staged_scope_violation")
    git("commit", "-m", "[skip ci] Record v0.2A.1 no-network import diagnostic")
    git("push", "origin", f"HEAD:{BRANCH}")
    print("STATUS=" + result["status"])
    print("NETWORK_ATTEMPTS=" + str(result["network_attempt_count"]))
    print("MODEL_INVOCATIONS=0")
    print("PUBLISHED_COMMIT=" + git("rev-parse", "HEAD", capture=True))
    print("RESULT_PATH=" + str(DIAGNOSTIC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
