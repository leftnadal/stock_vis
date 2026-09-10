#!/usr/bin/env python3
"""No-network, no-count diagnostic for the preserved chat-template ImportError."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import sys
import traceback
from pathlib import Path


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitize_path(value: str, snapshot: Path, environment: Path) -> str:
    return value.replace(str(snapshot), "<tokenizer_snapshot>").replace(
        str(environment), "<experiment_environment>"
    )


def candidate_module(error: BaseException) -> str | None:
    if isinstance(error, ModuleNotFoundError) and error.name:
        return error.name
    message = str(error)
    patterns = (
        r"No module named ['\"]([^'\"]+)",
        r"requires (?:the )?['\"]?([A-Za-z0-9_.-]+)['\"]? (?:library|package|to be installed)",
    )
    for pattern in patterns:
        found = re.search(pattern, message, flags=re.IGNORECASE)
        if found:
            return found.group(1)
    return None


def installed_packages() -> list[str]:
    rows = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            rows.append(f"{name}=={dist.version}")
    return sorted(set(rows), key=str.lower)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--asset-manifest", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    os.environ.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "NO_PROXY": "*",
        "no_proxy": "*",
    })
    network_events: list[str] = []

    def deny_network(event: str, _args) -> None:
        if event in {"socket.connect", "socket.bind"}:
            network_events.append(event)
            raise RuntimeError("network_operation_denied_by_diagnostic")

    sys.addaudithook(deny_network)
    manifest = json.loads(args.asset_manifest.read_text())
    for row in manifest["assets"]:
        path = args.snapshot / row["path"]
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise ValueError("preserved_tokenizer_asset_integrity_failure")

    import tokenizers
    import transformers

    tokenizer = transformers.AutoTokenizer.from_pretrained(
        args.snapshot,
        local_files_only=True,
        trust_remote_code=False,
        use_fast=True,
    )
    result = {
        "diagnostic": "Replay v0.2A.1 chat-template ImportError no-network diagnostic",
        "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": {
            "network_allowed": False,
            "package_installation_allowed": False,
            "historical_request_used": False,
            "historical_count_gate_rerun": False,
            "provider_or_model_invocations": 0,
            "tokenizer_assets_modified": False,
        },
        "environment": str(args.environment),
        "snapshot": str(args.snapshot),
        "immutable_revision": manifest["immutable_revision"],
        "asset_integrity": "passed",
        "tokenizer": {
            "class": type(tokenizer).__name__,
            "is_fast": bool(getattr(tokenizer, "is_fast", False)),
            "transformers_version": transformers.__version__,
            "tokenizers_version": tokenizers.__version__,
        },
        "installed_packages": installed_packages(),
    }
    try:
        tokenizer.apply_chat_template(
            [{"role": "user", "content": "diagnostic"}],
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception as exc:
        module = candidate_module(exc)
        frames = []
        for frame in traceback.extract_tb(exc.__traceback__):
            frames.append({
                "file": sanitize_path(frame.filename, args.snapshot, args.environment),
                "line": frame.lineno,
                "function": frame.name,
            })
        result.update({
            "status": "diagnosed_import_failure",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "candidate_missing_module": module,
            "candidate_module_importable": (
                importlib.util.find_spec(module) is not None if module else None
            ),
            "traceback_frames": frames,
        })
    else:
        result.update({
            "status": "minimal_call_did_not_reproduce_import_failure",
            "exception_type": None,
            "candidate_missing_module": None,
            "candidate_module_importable": None,
            "traceback_frames": [],
        })
    result["network_attempts"] = network_events
    result["network_attempt_count"] = len(network_events)
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(dump(result))
    print("DIAGNOSTIC_STATUS=" + result["status"])
    print("CANDIDATE_MISSING_MODULE=" + str(result["candidate_missing_module"]))
    print("NETWORK_ATTEMPTS=" + str(result["network_attempt_count"]))
    print("MODEL_INVOCATIONS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
