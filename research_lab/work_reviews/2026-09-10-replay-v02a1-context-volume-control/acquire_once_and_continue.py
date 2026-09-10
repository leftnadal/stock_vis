#!/usr/bin/env python3
"""One official acquisition attempt, exact gate, then at most two model calls."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import provider_adapter as provider
from acquisition_contract import (
    ACQUISITION_ID, MODEL_REPOSITORY, PYPI_INDEX, TOKENIZERS_PIN,
    TRANSFORMERS_PIN, pip_download_command, pip_install_command, sha256_file,
)

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO = SCRIPT_ROOT.parents[2]
BRANCH = "feature/research-replay-v02a1-context-volume-control"
RUN_ROOT = SCRIPT_ROOT / "acquisition_runs" / ACQUISITION_ID
EXTERNAL_ROOT = SCRIPT_ROOT.parents[3] / ".experiments" / f"replay-v02a1-{ACQUISITION_ID}"


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def git(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def run(args: list[str], *, env=None, capture=False) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, check=True, text=True, env=env,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def task_path(path: Path) -> str:
    return str(path.relative_to(REPO))


def verify_start() -> None:
    if git("branch", "--show-current", capture=True) != BRANCH:
        raise RuntimeError("wrong_branch")
    if subprocess.run(["git", "diff", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("tracked_worktree_changes_present")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("preexisting_staged_changes_present")
    if RUN_ROOT.exists() or EXTERNAL_ROOT.exists():
        raise RuntimeError("official_acquisition_attempt_already_exists")


def verify_staged(prefix: Path) -> None:
    staged = git("diff", "--cached", "--name-only", capture=True).splitlines()
    allowed = task_path(prefix).rstrip("/") + "/"
    if not staged or any(not path.startswith(allowed) for path in staged):
        raise RuntimeError("staged_scope_violation")


def publish(paths: list[Path], message: str) -> str:
    git("add", *[task_path(path) for path in paths])
    verify_staged(RUN_ROOT)
    git("commit", "-m", message)
    git("push", "origin", f"HEAD:{BRANCH}")
    return git("rev-parse", "HEAD", capture=True)


def safe_failure(status: str, stage: str, exc: BaseException, base: dict) -> dict:
    return {
        **base,
        "status": status,
        "failed_stage": stage,
        "safe_error_type": type(exc).__name__,
        "finished_at": now(),
        "model_invocations": 0,
        "no_alternative_search_performed": True,
        "historical_artifacts_modified": False,
    }


def write_checksums() -> None:
    files = sorted(
        path for path in RUN_ROOT.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    )
    (RUN_ROOT / "SHA256SUMS").write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(RUN_ROOT)}\n" for path in files)
    )


def package_manifest(wheel_dir: Path, freeze: str, started_at: str) -> dict:
    artifacts = []
    for path in sorted(wheel_dir.iterdir()):
        if path.is_file():
            artifacts.append({
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "source_index": PYPI_INDEX,
            })
    return {
        "source": "official PyPI",
        "source_index": PYPI_INDEX,
        "direct_dependencies": [
            {
                "name": "transformers", "version": TRANSFORMERS_PIN,
                "project_locator": f"https://pypi.org/project/transformers/{TRANSFORMERS_PIN}/",
            },
            {
                "name": "tokenizers", "version": TOKENIZERS_PIN,
                "project_locator": f"https://pypi.org/project/tokenizers/{TOKENIZERS_PIN}/",
            },
        ],
        "downloaded_artifacts_including_transitives": artifacts,
        "installed_packages_freeze": freeze.splitlines(),
        "install_started_at": started_at,
        "install_completed_at": now(),
        "python": sys.version,
        "platform": platform.platform(),
        "environment_path": str(EXTERNAL_ROOT / "venv"),
        "environment_scope": "experiment-local",
    }


def verify_installed_pins(freeze: str) -> None:
    normalized = {line.strip().lower() for line in freeze.splitlines()}
    expected = {
        f"transformers=={TRANSFORMERS_PIN}".lower(),
        f"tokenizers=={TOKENIZERS_PIN}".lower(),
    }
    if not expected <= normalized:
        raise ValueError("installed_direct_dependency_pin_mismatch")


def load_token() -> str:
    token = os.environ.get("DEEPINFRA_TOKEN") or os.environ.get("DEEP_INFRA_API_KEY")
    if not token:
        token = provider.token_from_file(SCRIPT_ROOT.parents[3] / ".env")
    return provider.valid_token(token or "")


def scan_and_manifest_execution(token: str) -> Path:
    execution_root = RUN_ROOT / "gate" / "executions"
    batches = [path for path in execution_root.iterdir() if path.is_dir()]
    if len(batches) != 1:
        raise RuntimeError("expected_exactly_one_execution_batch")
    batch = batches[0]
    token_bytes = token.encode()
    files = sorted(path for path in batch.rglob("*") if path.is_file())
    for path in files:
        data = path.read_bytes()
        if token_bytes in data or b"Authorization: Bearer" in data:
            raise RuntimeError("credential_material_detected")
    manifest = {
        "batch_id": batch.name,
        "credential_material_check": "passed",
        "model_run_limit": 2,
        "retries": 0,
        "selective_rerun": False,
        "files": [
            {"path": str(path.relative_to(RUN_ROOT)), "bytes": path.stat().st_size,
             "sha256": sha256_file(path)} for path in files
        ],
    }
    (batch / "ARTIFACT_MANIFEST.json").write_text(dump(manifest))
    return batch


def main() -> int:
    verify_start()
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS_ACQUISITION_PREP"],
        cwd=SCRIPT_ROOT, check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_acquisition", "test_preflight",
         "test_completion_contract", "test_publisher"],
        cwd=SCRIPT_ROOT, check=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    EXTERNAL_ROOT.mkdir(parents=True, exist_ok=False)
    wheel_dir = EXTERNAL_ROOT / "wheels"
    wheel_dir.mkdir()
    venv = EXTERNAL_ROOT / "venv"
    base = {
        "experiment": "Research Evidence Handoff Replay v0.2A.1",
        "acquisition_id": ACQUISITION_ID,
        "attempt_limit": 1,
        "attempt_number": 1,
        "started_at": now(),
        "official_model_repository": MODEL_REPOSITORY,
        "pinned_stack": {
            "transformers": TRANSFORMERS_PIN, "tokenizers": TOKENIZERS_PIN,
        },
        "external_environment_path": str(EXTERNAL_ROOT),
        "model_invocations": 0,
    }
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    py = venv / "bin" / "python"
    install_started = now()
    try:
        run(pip_download_command(py, wheel_dir))
        run(pip_install_command(py, wheel_dir))
        freeze = run([str(py), "-m", "pip", "freeze", "--all"], capture=True).stdout
        verify_installed_pins(freeze)
    except Exception as exc:
        RUN_ROOT.mkdir(parents=True, exist_ok=False)
        base["dependency_artifacts"] = [
            {"filename": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p),
             "source_index": PYPI_INDEX} for p in sorted(wheel_dir.glob("*")) if p.is_file()
        ]
        result = safe_failure("dependency_resolution_blocked", "official_pypi_resolution", exc, base)
        (RUN_ROOT / "acquisition_result.json").write_text(dump(result))
        write_checksums()
        commit = publish([RUN_ROOT], "[skip ci] Record blocked v0.2A.1 pinned dependency acquisition")
        print("STATUS=dependency_resolution_blocked\nMODEL_INVOCATIONS=0\nPUBLISHED_COMMIT=" + commit)
        return 0

    RUN_ROOT.mkdir(parents=True, exist_ok=False)
    (RUN_ROOT / "dependency_manifest.json").write_text(
        dump(package_manifest(wheel_dir, freeze, install_started))
    )
    asset_external = EXTERNAL_ROOT / "tokenizer_asset_manifest.json"
    try:
        run([
            str(py), str(SCRIPT_ROOT / "hf_acquire.py"),
            "--external-root", str(EXTERNAL_ROOT), "--output", str(asset_external),
        ])
        asset_manifest = json.loads(asset_external.read_text())
        (RUN_ROOT / "tokenizer_asset_manifest.json").write_text(dump(asset_manifest))
        offline = os.environ.copy()
        offline.update({
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONDONTWRITEBYTECODE": "1",
        })
        gate = subprocess.run([
            str(py), str(SCRIPT_ROOT / "acquired_preflight.py"),
            "--snapshot", asset_manifest["snapshot_path"],
            "--output-root", str(RUN_ROOT / "gate"),
            "--revision", asset_manifest["immutable_revision"],
        ], env=offline)
        gate_result = json.loads((RUN_ROOT / "gate" / "preflight_result.json").read_text())
    except Exception as exc:
        result = safe_failure("blocked_tokenizer_integrity_failure", "official_asset_or_offline_load", exc, base)
        (RUN_ROOT / "acquisition_result.json").write_text(dump(result))
        write_checksums()
        commit = publish([RUN_ROOT], "[skip ci] Record blocked v0.2A.1 tokenizer integrity gate")
        print("STATUS=blocked_tokenizer_integrity_failure\nMODEL_INVOCATIONS=0\nPUBLISHED_COMMIT=" + commit)
        return 0

    base.update({
        "dependency_provenance_complete": True,
        "tokenizer_asset_provenance_complete": True,
        "network_disabled_after_acquisition": True,
        "gate_status": gate_result["status"],
        "historical_reference_counts": gate_result.get("reference_counts"),
        "finished_at": now(),
    })
    if gate.returncode != 0 or gate_result["status"] != "ready_for_fixed_execution":
        base.update({
            "status": gate_result["status"],
            "model_invocations": 0,
            "no_alternative_search_performed": True,
            "historical_artifacts_modified": False,
        })
        (RUN_ROOT / "acquisition_result.json").write_text(dump(base))
        write_checksums()
        commit = publish([RUN_ROOT], "[skip ci] Record blocked v0.2A.1 exact tokenizer gate")
        print("STATUS=" + gate_result["status"] + "\nMODEL_INVOCATIONS=0\nPUBLISHED_COMMIT=" + commit)
        return 0

    base["status"] = "gate_passed_ready_for_fixed_execution"
    (RUN_ROOT / "acquisition_result.json").write_text(dump(base))
    write_checksums()
    preflight_commit = publish([RUN_ROOT], "[skip ci] Seal v0.2A.1 official tokenizer gate and inputs")

    token = load_token()
    execution_env = offline.copy()
    execution_env["REPLAY_EXPERIMENT_ROOT"] = str(RUN_ROOT / "gate")
    execution = subprocess.run([str(py), str(SCRIPT_ROOT / "replay.py")], env=execution_env)
    execution_manifests = list((RUN_ROOT / "gate" / "executions").glob("*/manifest.json"))
    if len(execution_manifests) != 1:
        raise RuntimeError("execution_manifest_missing_or_ambiguous")
    execution_ledger = json.loads(execution_manifests[0].read_text())
    base["model_invocations"] = execution_ledger["model_invocations"]
    (RUN_ROOT / "acquisition_result.json").write_text(dump(base))
    batch = scan_and_manifest_execution(token)
    write_checksums()
    commit = publish([RUN_ROOT], "[skip ci] Add v0.2A.1 context-volume execution evidence")
    print("STATUS=" + ("execution_finished" if execution.returncode == 0 else "systemic_execution_error"))
    print("PREFLIGHT_COMMIT=" + preflight_commit)
    print("RESULT_PATH=" + str(batch))
    print("PUBLISHED_COMMIT=" + commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
