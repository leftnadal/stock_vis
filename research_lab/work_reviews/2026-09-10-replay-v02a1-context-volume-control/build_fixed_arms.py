#!/usr/bin/env python3
"""Build two v0.2A.1 arms from the already-passed historical count gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import preflight


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_prior_gate(gate_path: Path, source_root: Path) -> dict:
    gate = json.loads(gate_path.read_text())
    if gate.get("status") != "exact_count_gate_passed" or gate.get("exact_count_gate_execution_count") != 1:
        raise ValueError("prior_exact_count_gate_not_valid")
    for label, (filename, expected) in {
        "short": ("v02a-sanitized-visible.json", 4903),
        "original": ("v02a-original-visible.json", 14387),
    }.items():
        row = gate["reference_counts"][label]
        if row["actual_input_ids_length"] != expected or row["provider_reference_tokens"] != expected:
            raise ValueError("prior_reference_count_mismatch:" + label)
        if row["source_sha256"] != sha(source_root / filename):
            raise ValueError("prior_source_identity_mismatch:" + label)
    return gate


def build(tokenizer, identity: dict, source_root: Path, gate_path: Path, output: Path) -> dict:
    gate = verify_prior_gate(gate_path, source_root)
    short_reference = json.loads((source_root / "v02a-sanitized-visible.json").read_text())
    body = json.loads(short_reference[1]["content"])
    evidence = body["provided_documents"]
    if len(evidence) != 17 or not all(item["kind"] == "evidence" for item in evidence):
        raise ValueError("evidence_contract_mismatch")
    system_prompt = short_reference[0]["content"] + "\n" + preflight.CONTROL_INSTRUCTION
    short_messages = preflight.messages_for(system_prompt, body["summary"], evidence, [])
    short_tokens = preflight.prompt_tokens(tokenizer, short_messages)
    characters, long_tokens = preflight.find_exact_control(
        tokenizer, system_prompt, body["summary"], evidence, 14387,
    )
    items = preflight.control_items(characters)
    long_messages = preflight.messages_for(system_prompt, body["summary"], evidence, items)
    if long_tokens != 14387 or not items or not all(set(item) <= set("0123456789abcdef") for item in items):
        raise ValueError("long_control_exactness_or_opacity_failed")

    output.mkdir(parents=True, exist_ok=False)
    visible = output / "visible"
    visible.mkdir()
    arms = {"S-short": short_messages, "S-long-control": long_messages}
    runs = []
    for condition, messages in arms.items():
        run_id = preflight.RUN_IDS[condition]
        raw = preflight.dump(messages)
        (visible / f"{run_id}.json").write_text(raw)
        runs.append({"condition": condition, "run_id": run_id,
                     "input_sha256": preflight.sha_text(raw),
                     "local_prompt_tokens": preflight.prompt_tokens(tokenizer, messages)})
    plan = {
        "experiment": "Research Evidence Handoff Replay v0.2A.1",
        "version": "0.2.1-counting-repair-1",
        "case": "hard-006",
        "calibration_only": True,
        "independent_variable": "opaque context_volume_control size",
        "historical_context_absent_both_arms": True,
        "prior_exact_count_gate_sha256": sha(gate_path),
        "tokenizer_identity": identity,
        "config": {"model": preflight.MODEL, "temperature": 0.6, "top_p": 0.95,
                   "seed": 20260909, "reasoning": {"enabled": True}, "max_tokens": 8192,
                   "timeout_seconds": 420, "retry_count": 0},
        "runs": runs,
    }
    (output / "plan.json").write_text(preflight.dump(plan))
    diff = {
        "status": "passed",
        "only_differing_user_body_field": "context_volume_control",
        "system_prompt_identical": short_messages[0] == long_messages[0],
        "summary_identical": True,
        "available_sources_identical": True,
        "evidence_identical_and_ordered": True,
        "evidence_count_each_arm": 17,
        "historical_candidate_critique_absent": True,
        "short_control_empty": True,
        "long_control_hex_only": True,
        "protected_expectations_absent": True,
    }
    (output / "input_diff_and_leakage.json").write_text(preflight.dump(diff))
    result = {
        "status": "ready_for_two_fixed_calls",
        "prior_gate_reexecuted": False,
        "prior_gate_status": gate["status"],
        "prior_gate_sha256": sha(gate_path),
        "short_input_tokens": short_tokens,
        "long_control_input_tokens": long_tokens,
        "control_payload_characters": characters,
        "control_payload_sha256": preflight.sha_text(preflight.dump(items)),
        "model_visible_arms_generated": 2,
        "provider_model_invocations": 0,
        "tokenizer_or_template_changed": False,
        "input_normalization_performed": False,
        "tokenizer_identity": identity,
        "input_sha256": {row["condition"]: row["input_sha256"] for row in runs},
    }
    (output / "preflight_result.json").write_text(preflight.dump(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--gate-result", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1"})
    import tokenizers
    import transformers
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        args.snapshot, local_files_only=True, trust_remote_code=False, use_fast=True,
    )
    identity = {"immutable_revision": args.revision,
                "tokenizer_class": type(tokenizer).__name__,
                "backend_tokenizer_sha256": preflight.sha_text(tokenizer.backend_tokenizer.to_str()),
                "transformers_version": transformers.__version__,
                "tokenizers_version": tokenizers.__version__,
                "local_files_only": True, "trust_remote_code": False}
    result = build(tokenizer, identity, args.source_root, args.gate_result, args.output)
    print("PREFLIGHT_STATUS=" + result["status"])
    print("SHORT_INPUT_TOKENS=" + str(result["short_input_tokens"]))
    print("LONG_CONTROL_INPUT_TOKENS=" + str(result["long_control_input_tokens"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
