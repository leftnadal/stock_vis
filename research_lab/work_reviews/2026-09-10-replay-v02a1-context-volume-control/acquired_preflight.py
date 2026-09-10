#!/usr/bin/env python3
"""Load an acquired tokenizer offline and run the strict historical count gate."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import preflight


def verify_and_record_input_diff(output_root: Path) -> dict:
    plan = json.loads((output_root / "plan.json").read_text())
    by_condition = {row["condition"]: row for row in plan["runs"]}
    short = json.loads((output_root / "visible" / f"{by_condition['S-short']['run_id']}.json").read_text())
    long = json.loads((output_root / "visible" / f"{by_condition['S-long-control']['run_id']}.json").read_text())
    if short[0] != long[0]:
        raise ValueError("system_prompt_differs_between_arms")
    short_body = json.loads(short[1]["content"])
    long_body = json.loads(long[1]["content"])
    if set(short_body) != {"summary", "available_sources", "provided_documents", "context_volume_control"}:
        raise ValueError("unexpected_short_input_fields")
    if set(long_body) != set(short_body):
        raise ValueError("input_schema_differs_between_arms")
    for field in ("summary", "available_sources", "provided_documents"):
        if short_body[field] != long_body[field]:
            raise ValueError("material_input_diff_outside_control")
    if short_body["context_volume_control"] != []:
        raise ValueError("short_control_not_empty")
    items = long_body["context_volume_control"]
    if not items or any(not item or set(item) - set("0123456789abcdef") for item in items):
        raise ValueError("long_control_not_opaque_hex")
    if any(key in short_body or key in long_body for key in ("expected_label", "answer_key", "candidate_answer", "critique")):
        raise ValueError("protected_or_historical_field_visible")
    result = {
        "status": "passed",
        "only_differing_field": "context_volume_control",
        "system_prompt_identical": True,
        "summary_identical": True,
        "available_sources_identical": True,
        "evidence_identical": True,
        "evidence_count_each_arm": len(short_body["provided_documents"]),
        "short_control_empty": True,
        "long_control_hex_only": True,
        "historical_candidate_critique_fields_absent": True,
        "answer_key_or_expected_label_fields_absent": True,
    }
    (output_root / "input_diff_and_leakage.json").write_text(preflight.dump(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    import tokenizers
    import transformers

    args.output_root.mkdir(parents=True, exist_ok=False)
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        args.snapshot,
        local_files_only=True,
        trust_remote_code=False,
        use_fast=True,
    )
    if not getattr(tokenizer, "is_fast", False):
        raise ValueError("fast_tokenizer_required")
    if not callable(getattr(tokenizer, "apply_chat_template", None)):
        raise ValueError("apply_chat_template_unavailable")
    backend = tokenizer.backend_tokenizer.to_str().encode()
    identity = {
        "requested_model": preflight.MODEL,
        "immutable_revision": args.revision,
        "tokenizer_class": type(tokenizer).__name__,
        "name_or_path": str(args.snapshot.resolve()),
        "vocab_size": int(getattr(tokenizer, "vocab_size", 0)),
        "transformers_version": transformers.__version__,
        "tokenizers_version": tokenizers.__version__,
        "backend_tokenizer_sha256": preflight.sha_bytes(backend),
        "local_files_only": True,
        "trust_remote_code": False,
        "use_fast": True,
        "is_fast": True,
        "apply_chat_template_available": True,
        "offline_environment": {
            "HF_HUB_OFFLINE": os.environ["HF_HUB_OFFLINE"],
            "TRANSFORMERS_OFFLINE": os.environ["TRANSFORMERS_OFFLINE"],
        },
    }
    preflight.ROOT = args.output_root
    preflight.SOURCE = Path(__file__).resolve().parent / "source_snapshot"
    result = preflight.run_preflight(tokenizer=tokenizer, tokenizer_identity=identity)
    if result.get("blocker") == "local_tokenizer_does_not_reproduce_provider_reference_counts":
        result["status"] = "blocked_tokenizer_accounting_mismatch"
        result["no_alternative_search_performed"] = True
    elif result["status"] != "ready_for_fixed_execution":
        result["status"] = "blocked_tokenizer_integrity_failure"
        result["no_alternative_search_performed"] = True
    else:
        result["input_diff_and_leakage"] = verify_and_record_input_diff(args.output_root)
    (args.output_root / "preflight_result.json").write_text(preflight.dump(result))
    print("PREFLIGHT_STATUS=" + result["status"])
    return 0 if result["status"] == "ready_for_fixed_execution" else 2


if __name__ == "__main__":
    raise SystemExit(main())
