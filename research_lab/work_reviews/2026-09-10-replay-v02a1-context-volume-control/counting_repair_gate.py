#!/usr/bin/env python3
"""One offline historical exact-count gate; never builds experiment arms."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

import preflight


REFERENCES = {
    "short": ("v02a-sanitized-visible.json", 4903),
    "original": ("v02a-original-visible.json", 14387),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def top_level_len(value) -> int | None:
    return len(value) if hasattr(value, "__len__") else None


def run_gate(tokenizer, source_root: Path, identity: dict) -> dict:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    counts = {}
    for label, (filename, provider_count) in REFERENCES.items():
        source = source_root / filename
        messages = json.loads(source.read_text())
        tokenized = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
        )
        actual = preflight.prompt_tokens_from_result(tokenized)
        counts[label] = {
            "source_path": f"source_snapshot/{filename}",
            "source_sha256": sha(source),
            "legacy_top_level_len": top_level_len(tokenized),
            "actual_input_ids_length": actual,
            "provider_reference_tokens": provider_count,
            "exact_match": actual == provider_count,
        }
    passed = all(row["exact_match"] for row in counts.values())
    return {
        "experiment": "Research Evidence Handoff Replay v0.2A.1",
        "lineage": "counting-repair-gate-001",
        "status": "exact_count_gate_passed" if passed else "exact_count_gate_failed",
        "execution_started_at": started,
        "execution_finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "counting_repair": "use actual input_ids sequence length instead of BatchEncoding key count",
        "exact_count_gate_execution_count": 1,
        "reference_counts": counts,
        "tokenizer_identity": identity,
        "network_attempts": 0,
        "provider_model_invocations": 0,
        "model_visible_arms_generated": 0,
        "input_normalization_performed": False,
        "tokenizer_or_template_changed": False,
        "historical_artifacts_modified": False,
        "runtime": {"python": sys.version, "platform": platform.platform()},
    }


def load_tokenizer(snapshot: Path, revision: str):
    os.environ.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    })
    import tokenizers
    import transformers

    tokenizer = transformers.AutoTokenizer.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False, use_fast=True,
    )
    identity = {
        "immutable_revision": revision,
        "tokenizer_class": type(tokenizer).__name__,
        "name_or_path": str(snapshot.resolve()),
        "vocab_size": int(getattr(tokenizer, "vocab_size", 0)),
        "transformers_version": transformers.__version__,
        "tokenizers_version": tokenizers.__version__,
        "backend_tokenizer_sha256": preflight.sha_text(tokenizer.backend_tokenizer.to_str()),
        "local_files_only": True,
        "trust_remote_code": False,
    }
    return tokenizer, identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tokenizer, identity = load_tokenizer(args.snapshot, args.revision)
    result = run_gate(tokenizer, args.source_root, identity)
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(preflight.dump(result))
    print("COUNTING_REPAIR_GATE=" + result["status"])
    print("MODEL_VISIBLE_ARMS_GENERATED=0")
    print("PROVIDER_MODEL_INVOCATIONS=0")
    return 0 if result["status"] == "exact_count_gate_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
