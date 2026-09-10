#!/usr/bin/env python3
"""One Jinja correction acquisition, exact-count gate, and at most two calls."""
from __future__ import annotations

import datetime
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from jinja_correction_contract import (
    CORRECTION_ID,
    JINJA2_PIN,
    MARKUPSAFE_PIN,
    ORIGINAL_ACQUISITION_ID,
    PYPI_INDEX,
    TOKENIZERS_PIN,
    TRANSFORMERS_PIN,
    download_command,
    install_command,
    sha256_file,
    verify_freeze,
    verify_original_files,
)

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO = SCRIPT_ROOT.parents[2]
BRANCH = "feature/research-replay-v02a1-context-volume-control"
ORIGINAL_RUN = SCRIPT_ROOT / "acquisition_runs" / ORIGINAL_ACQUISITION_ID
CORRECTION_ROOT = ORIGINAL_RUN / "continuations" / CORRECTION_ID
EXPERIMENTS = SCRIPT_ROOT.parents[3] / ".experiments"
ORIGINAL_EXTERNAL = EXPERIMENTS / f"replay-v02a1-{ORIGINAL_ACQUISITION_ID}"
CORRECTION_EXTERNAL = EXPERIMENTS / f"replay-v02a1-{CORRECTION_ID}"


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


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


def repo_path(path: Path) -> str:
    return str(path.relative_to(REPO))


def verify_start() -> None:
    if git("branch", "--show-current", capture=True) != BRANCH:
        raise RuntimeError("wrong_branch")
    if subprocess.run(["git", "diff", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("tracked_worktree_changes_present")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode:
        raise RuntimeError("preexisting_staged_changes_present")
    if CORRECTION_ROOT.exists() or CORRECTION_EXTERNAL.exists():
        raise RuntimeError("jinja_correction_attempt_already_exists")
    for required in (
        ORIGINAL_RUN / "dependency_manifest.json",
        ORIGINAL_RUN / "tokenizer_asset_manifest.json",
        ORIGINAL_RUN / "SHA256SUMS",
        ORIGINAL_EXTERNAL / "wheels",
        ORIGINAL_EXTERNAL / "tokenizer_snapshot",
    ):
        if not required.exists():
            raise RuntimeError("original_acquisition_material_missing:" + required.name)


def verify_staged_additions() -> None:
    lines = git("diff", "--cached", "--name-status", capture=True).splitlines()
    prefix = repo_path(CORRECTION_ROOT).rstrip("/") + "/"
    if not lines:
        raise RuntimeError("nothing_staged")
    for line in lines:
        status, path = line.split("\t", 1)
        if status != "A" or not path.startswith(prefix):
            raise RuntimeError("append_only_staged_scope_violation")


def publish(message: str) -> str:
    git("add", repo_path(CORRECTION_ROOT))
    verify_staged_additions()
    git("commit", "-m", message)
    git("push", "origin", f"HEAD:{BRANCH}")
    return git("rev-parse", "HEAD", capture=True)


def write_hash_list(path: Path, files: list[Path], base: Path) -> None:
    path.write_text("".join(
        f"{sha256_file(item)}  {item.relative_to(base)}\n" for item in sorted(files)
    ))


def safe_failure(base: dict, status: str, stage: str, exc: BaseException) -> dict:
    return {
        **base,
        "status": status,
        "failed_stage": stage,
        "safe_error_type": type(exc).__name__,
        "finished_at": now(),
        "network_acquisition_command_attempts": base.get(
            "network_acquisition_command_attempts", 0
        ),
        "model_invocations": 0,
        "historical_artifacts_modified": False,
        "alternative_dependency_or_tokenizer_search": False,
    }


def record_blocked(base: dict, status: str, stage: str, exc: BaseException) -> int:
    CORRECTION_ROOT.mkdir(parents=True, exist_ok=False)
    result = safe_failure(base, status, stage, exc)
    result_path = CORRECTION_ROOT / "correction_result.json"
    result_path.write_text(dump(result))
    write_hash_list(CORRECTION_ROOT / "GATE_SHA256SUMS", [result_path], CORRECTION_ROOT)
    commit = publish("[skip ci] Record blocked v0.2A.1 Jinja correction")
    print(f"STATUS={status}\nMODEL_INVOCATIONS=0\nPUBLISHED_COMMIT={commit}")
    return 0


def verify_original_material() -> tuple[dict, dict, list[dict], list[dict]]:
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS"],
        cwd=ORIGINAL_RUN, check=True,
    )
    dependency = json.loads((ORIGINAL_RUN / "dependency_manifest.json").read_text())
    asset = json.loads((ORIGINAL_RUN / "tokenizer_asset_manifest.json").read_text())
    wheels = verify_original_files(
        ORIGINAL_RUN / "dependency_manifest.json", ORIGINAL_EXTERNAL / "wheels",
        "downloaded_artifacts_including_transitives",
    )
    assets = verify_original_files(
        ORIGINAL_RUN / "tokenizer_asset_manifest.json", ORIGINAL_EXTERNAL / "tokenizer_snapshot",
        "assets",
    )
    return dependency, asset, wheels, assets


def correction_wheel_manifest(directory: Path) -> list[dict]:
    rows = []
    for path in sorted(directory.iterdir()):
        if path.is_file():
            rows.append({
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "source_index": PYPI_INDEX,
            })
    if len(rows) != 2:
        raise ValueError("expected_exactly_two_correction_wheels")
    names = {row["filename"].lower() for row in rows}
    if not any(name.startswith("jinja2-3.1.6-") for name in names):
        raise ValueError("pinned_jinja2_wheel_missing")
    if not any(name.startswith("markupsafe-3.0.2-") for name in names):
        raise ValueError("pinned_markupsafe_wheel_missing")
    return rows


def load_token() -> str:
    import provider_adapter as provider
    token = os.environ.get("DEEPINFRA_TOKEN") or os.environ.get("DEEP_INFRA_API_KEY")
    if not token:
        token = provider.token_from_file(SCRIPT_ROOT.parents[3] / ".env")
    return provider.valid_token(token or "")


def execution_files(batch: Path) -> list[Path]:
    return sorted(path for path in batch.rglob("*") if path.is_file())


def main() -> int:
    verify_start()
    subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS_JINJA_CORRECTION_PREP"],
        cwd=SCRIPT_ROOT, check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_jinja_correction",
         "test_preflight", "test_completion_contract"],
        cwd=SCRIPT_ROOT, check=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    dependency, asset, original_wheels, original_assets = verify_original_material()
    CORRECTION_EXTERNAL.mkdir(parents=True, exist_ok=False)
    correction_wheels = CORRECTION_EXTERNAL / "correction_wheels"
    correction_wheels.mkdir()
    venv = CORRECTION_EXTERNAL / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    py = venv / "bin" / "python"
    base = {
        "experiment": "Research Evidence Handoff Replay v0.2A.1",
        "correction_id": CORRECTION_ID,
        "parent_acquisition": ORIGINAL_ACQUISITION_ID,
        "started_at": now(),
        "pinned_stack": {
            "transformers": TRANSFORMERS_PIN,
            "tokenizers": TOKENIZERS_PIN,
            "Jinja2": JINJA2_PIN,
            "MarkupSafe": MARKUPSAFE_PIN,
        },
        "network_scope": "one official-PyPI download command for two exact wheels",
        "network_acquisition_command_attempts": 0,
        "model_invocations": 0,
        "historical_artifacts_modified": False,
        "original_wheels_verified": len(original_wheels),
        "original_tokenizer_assets_verified": len(original_assets),
        "external_environment_path": str(CORRECTION_EXTERNAL),
    }
    try:
        base["network_acquisition_command_attempts"] = 1
        run(download_command(py, correction_wheels))
        correction_artifacts = correction_wheel_manifest(correction_wheels)
        run(install_command(py, ORIGINAL_EXTERNAL / "wheels", correction_wheels))
        freeze = run([str(py), "-m", "pip", "freeze", "--all"], capture=True).stdout
        verify_freeze(freeze, dependency["installed_packages_freeze"])
    except Exception as exc:
        return record_blocked(base, "blocked_correction_dependency_stage", "pinned_jinja_acquisition", exc)

    CORRECTION_ROOT.mkdir(parents=True, exist_ok=False)
    dependency_result = {
        "status": "corrected_environment_ready",
        "source": "official PyPI",
        "source_index": PYPI_INDEX,
        "direct_correction_dependencies": [
            {"name": "Jinja2", "version": JINJA2_PIN,
             "project_locator": f"https://pypi.org/project/Jinja2/{JINJA2_PIN}/"},
            {"name": "MarkupSafe", "version": MARKUPSAFE_PIN,
             "project_locator": f"https://pypi.org/project/MarkupSafe/{MARKUPSAFE_PIN}/"},
        ],
        "downloaded_correction_artifacts": correction_artifacts,
        "installed_packages_freeze": freeze.splitlines(),
        "python": sys.version,
        "platform": platform.platform(),
        "original_dependency_manifest_sha256": sha256_file(ORIGINAL_RUN / "dependency_manifest.json"),
        "original_asset_manifest_sha256": sha256_file(ORIGINAL_RUN / "tokenizer_asset_manifest.json"),
        "original_wheels_verified": original_wheels,
        "original_tokenizer_assets_verified": original_assets,
    }
    dependency_path = CORRECTION_ROOT / "correction_dependency_manifest.json"
    dependency_path.write_text(dump(dependency_result))
    offline = os.environ.copy()
    offline.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    gate_dir = CORRECTION_ROOT / "gate"
    try:
        gate = subprocess.run([
            str(py), str(SCRIPT_ROOT / "acquired_preflight.py"),
            "--snapshot", str(ORIGINAL_EXTERNAL / "tokenizer_snapshot"),
            "--output-root", str(gate_dir),
            "--revision", asset["immutable_revision"],
        ], env=offline)
        gate_result = json.loads((gate_dir / "preflight_result.json").read_text())
    except Exception as exc:
        result = safe_failure(base, "blocked_corrected_tokenizer_gate", "exact_count_gate", exc)
        result_path = CORRECTION_ROOT / "correction_result.json"
        result_path.write_text(dump(result))
        files = [p for p in CORRECTION_ROOT.rglob("*") if p.is_file()]
        write_hash_list(CORRECTION_ROOT / "GATE_SHA256SUMS", files, CORRECTION_ROOT)
        commit = publish("[skip ci] Record blocked v0.2A.1 corrected tokenizer gate")
        print("STATUS=blocked_corrected_tokenizer_gate\nMODEL_INVOCATIONS=0\nPUBLISHED_COMMIT=" + commit)
        return 0

    gate_ok = gate.returncode == 0 and gate_result.get("status") == "ready_for_fixed_execution"
    result = {
        **base,
        "status": "gate_passed_ready_for_fixed_execution" if gate_ok else gate_result.get("status"),
        "gate_status": gate_result.get("status"),
        "historical_reference_counts": gate_result.get("reference_counts"),
        "short_input_tokens": gate_result.get("short_input_tokens"),
        "long_control_input_tokens": gate_result.get("long_control_input_tokens"),
        "network_disabled_after_correction_acquisition": True,
        "correction_dependency_provenance_complete": True,
        "finished_at": now(),
        "model_invocations": 0,
    }
    result_path = CORRECTION_ROOT / "correction_result.json"
    result_path.write_text(dump(result))
    gate_files = [p for p in CORRECTION_ROOT.rglob("*") if p.is_file()]
    write_hash_list(CORRECTION_ROOT / "GATE_SHA256SUMS", gate_files, CORRECTION_ROOT)
    gate_commit = publish(
        "[skip ci] Seal v0.2A.1 Jinja correction gate"
        if gate_ok else "[skip ci] Record blocked v0.2A.1 exact-count correction gate"
    )
    if not gate_ok:
        print(f"STATUS={result['status']}\nMODEL_INVOCATIONS=0\nPUBLISHED_COMMIT={gate_commit}")
        return 0

    try:
        token = load_token()
    except Exception as exc:
        blocker = safe_failure(
            base, "blocked_before_fixed_execution", "credential_preflight", exc,
        )
        blocker["gate_commit"] = gate_commit
        blocker_path = CORRECTION_ROOT / "execution_blocker.json"
        blocker_path.write_text(dump(blocker))
        write_hash_list(
            CORRECTION_ROOT / "EXECUTION_BLOCKER_SHA256SUMS",
            [blocker_path], CORRECTION_ROOT,
        )
        commit = publish("[skip ci] Record blocked v0.2A.1 fixed execution")
        print("STATUS=blocked_before_fixed_execution")
        print("MODEL_INVOCATIONS=0")
        print("GATE_COMMIT=" + gate_commit)
        print("PUBLISHED_COMMIT=" + commit)
        return 0
    execution_env = offline.copy()
    execution_env["REPLAY_EXPERIMENT_ROOT"] = str(gate_dir)
    execution = subprocess.run([str(py), str(SCRIPT_ROOT / "replay.py")], env=execution_env)
    batches = [path for path in (gate_dir / "executions").iterdir() if path.is_dir()]
    if len(batches) != 1:
        raise RuntimeError("expected_exactly_one_execution_batch")
    batch = batches[0]
    token_bytes = token.encode()
    raw_files = execution_files(batch)
    for path in raw_files:
        data = path.read_bytes()
        if token_bytes in data or b"Authorization: Bearer" in data:
            raise RuntimeError("credential_material_detected")
    ledger = json.loads((batch / "manifest.json").read_text())
    execution_record = {
        "status": "execution_finished" if execution.returncode == 0 else "systemic_execution_error",
        "batch_id": batch.name,
        "gate_commit": gate_commit,
        "model_invocations": ledger.get("model_invocations"),
        "model_run_limit": 2,
        "retries": 0,
        "selective_rerun": False,
        "credential_material_check": "passed",
        "historical_artifacts_modified": False,
        "finished_at": now(),
    }
    record_path = CORRECTION_ROOT / "execution_record.json"
    record_path.write_text(dump(execution_record))
    execution_files_now = execution_files(batch) + [record_path]
    write_hash_list(
        CORRECTION_ROOT / "EXECUTION_SHA256SUMS", execution_files_now, CORRECTION_ROOT,
    )
    commit = publish("[skip ci] Add v0.2A.1 corrected context-volume evidence")
    print("STATUS=" + execution_record["status"])
    print("MODEL_INVOCATIONS=" + str(execution_record["model_invocations"]))
    print("GATE_COMMIT=" + gate_commit)
    print("PUBLISHED_COMMIT=" + commit)
    print("RESULT_PATH=" + str(batch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
