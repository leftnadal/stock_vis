#!/usr/bin/env python3
"""No-network/no-model rendering and token-accounting diagnostic for v0.2A.1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


PROVIDER_REFERENCE = {"short": 4903, "original": 14387}
SOURCE_NAMES = {
    "short": "v02a-sanitized-visible.json",
    "original": "v02a-original-visible.json",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_text(value: str) -> str:
    return sha_bytes(value.encode("utf-8"))


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def marker_observation(content: str, rendered: str) -> dict[str, Any]:
    width = min(96, len(content))
    first = content[:width]
    last = content[-width:]
    return {
        "content_characters": len(content),
        "content_sha256": sha_text(content),
        "full_content_present": content in rendered,
        "first_marker": {
            "characters": width,
            "sha256": sha_text(first),
            "present": first in rendered,
        },
        "last_marker": {
            "characters": width,
            "sha256": sha_text(last),
            "present": last in rendered,
        },
    }


def _shape(value: Any) -> list[int] | None:
    shape = getattr(value, "shape", None)
    if shape is not None:
        try:
            return [int(item) for item in shape]
        except (TypeError, ValueError):
            return None
    if isinstance(value, (list, tuple)):
        if not value:
            return [0]
        if isinstance(value[0], (list, tuple)):
            return [len(value), len(value[0])]
        return [len(value)]
    return None


def inspect_tokenized(result: Any) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "python_type": f"{type(result).__module__}.{type(result).__name__}",
        "top_level_len": len(result) if hasattr(result, "__len__") else None,
        "is_list": isinstance(result, list),
        "is_dict": isinstance(result, dict),
    }
    keys: list[str] = []
    if hasattr(result, "keys"):
        try:
            keys = sorted(str(key) for key in result.keys())
        except Exception:
            keys = []
    observation["keys"] = keys
    has_input_ids = "input_ids" in keys
    observation["input_ids_present"] = has_input_ids

    token_value = result.get("input_ids") if has_input_ids else result
    observation["input_ids_type"] = (
        f"{type(token_value).__module__}.{type(token_value).__name__}"
    )
    observation["input_ids_shape"] = _shape(token_value)

    if isinstance(token_value, (list, tuple)):
        if token_value and isinstance(token_value[0], (list, tuple)):
            if len(token_value) != 1:
                observation["actual_token_sequence_length"] = None
                observation["count_status"] = "ambiguous_multiple_sequences"
            else:
                observation["actual_token_sequence_length"] = len(token_value[0])
                observation["count_status"] = "single_nested_sequence"
        else:
            observation["actual_token_sequence_length"] = len(token_value)
            observation["count_status"] = "single_flat_sequence"
    else:
        shape = observation["input_ids_shape"]
        if shape and len(shape) == 1:
            observation["actual_token_sequence_length"] = shape[0]
            observation["count_status"] = "single_shaped_sequence"
        elif shape and len(shape) == 2 and shape[0] == 1:
            observation["actual_token_sequence_length"] = shape[1]
            observation["count_status"] = "single_batched_sequence"
        else:
            observation["actual_token_sequence_length"] = None
            observation["count_status"] = "unassessed_structure"

    actual = observation["actual_token_sequence_length"]
    top = observation["top_level_len"]
    observation["top_level_len_differs_from_actual"] = (
        actual is not None and top is not None and actual != top
    )
    return observation


def diagnose(tokenizer: Any, source_root: Path, tokenizer_identity: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for label, filename in SOURCE_NAMES.items():
        source = source_root / filename
        raw = source.read_bytes()
        messages = json.loads(raw)
        try:
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
            if not isinstance(rendered, str):
                raise TypeError("tokenize_false_did_not_return_string")
            rendering = {
                "python_type": f"{type(rendered).__module__}.{type(rendered).__name__}",
                "characters": len(rendered),
                "bytes": len(rendered.encode("utf-8")),
                "sha256": sha_text(rendered),
                "messages": {
                    message["role"]: marker_observation(message["content"], rendered)
                    for message in messages
                },
                "full_body_included": all(
                    message["content"] in rendered for message in messages
                ),
            }
            tokenized = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
            )
            accounting = inspect_tokenized(tokenized)
            error = None
        except Exception as exc:
            rendering = None
            accounting = None
            error = {"type": type(exc).__name__, "message_sha256": sha_text(str(exc))}
        rows[label] = {
            "source": {
                "path": f"source_snapshot/{filename}",
                "bytes": len(raw),
                "sha256": sha_bytes(raw),
            },
            "provider_reference_tokens": PROVIDER_REFERENCE[label],
            "rendering": rendering,
            "token_accounting": accounting,
            "error": error,
        }

    if any(row["error"] for row in rows.values()):
        outcome = "D_diagnostic_failed"
        gate = "unassessed"
    elif any(not row["rendering"]["full_body_included"] for row in rows.values()):
        outcome = "B_historical_string_body_not_fully_rendered"
        gate = "not_rerun"
    elif any(
        row["token_accounting"]["actual_token_sequence_length"] is None
        for row in rows.values()
    ):
        outcome = "D_token_structure_ambiguous"
        gate = "unassessed"
    else:
        corrected = {
            label: row["token_accounting"]["actual_token_sequence_length"]
            for label, row in rows.items()
        }
        differs = any(
            row["token_accounting"]["top_level_len_differs_from_actual"]
            for row in rows.values()
        )
        matches = all(corrected[label] == PROVIDER_REFERENCE[label] for label in rows)
        if differs:
            # One counting-only gate re-evaluation; no input construction follows.
            gate = "passed" if matches else "failed"
            outcome = (
                "A_counting_defect_confirmed_exact_gate_passed"
                if matches else
                "A_counting_defect_confirmed_provider_mismatch_remains"
            )
        else:
            gate = "passed" if matches else "failed"
            outcome = (
                "C_valid_local_count_matches_reference"
                if matches else "C_valid_local_count_provider_mismatch_remains"
            )

    return {
        "experiment": "Research Evidence Handoff Replay v0.2A.1",
        "diagnostic": "raw-rendering-and-token-accounting-001",
        "status": "diagnostic_completed",
        "outcome": outcome,
        "tokenizer_identity": tokenizer_identity,
        "observations": rows,
        "corrected_exact_count_gate": gate,
        "fixed_experimental_arms_generated": 0,
        "model_provider_invocations": 0,
        "network_attempts": 0,
        "alternative_tokenizer_search": False,
        "input_normalization_performed": False,
        "historical_artifacts_modified": False,
        "interpretation_boundary": {
            "rendered_success_proves_provider_equivalence": False,
            "local_count_proves_provider_accounting": False,
            "count_equality_proves_internal_normalization": False,
        },
        "runtime": {"python": sys.version, "platform": platform.platform()},
    }


def load_tokenizer(snapshot: Path):
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
        "tokenizer_class": type(tokenizer).__name__,
        "name_or_path": str(getattr(tokenizer, "name_or_path", "")),
        "vocab_size": int(getattr(tokenizer, "vocab_size", 0)),
        "transformers_version": transformers.__version__,
        "tokenizers_version": tokenizers.__version__,
        "backend_tokenizer_sha256": sha_text(tokenizer.backend_tokenizer.to_str()),
        "local_files_only": True,
        "trust_remote_code": False,
    }
    return tokenizer, identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tokenizer, identity = load_tokenizer(args.snapshot)
    result = diagnose(tokenizer, args.source_root, identity)
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(dump(result))
    print("DIAGNOSTIC_OUTCOME=" + result["outcome"])
    print("MODEL_PROVIDER_INVOCATIONS=0")
    print("NETWORK_ATTEMPTS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
