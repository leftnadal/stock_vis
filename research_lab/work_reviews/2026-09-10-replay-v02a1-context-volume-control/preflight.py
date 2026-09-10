#!/usr/bin/env python3
"""Offline-only tokenizer gate and input builder for Replay v0.2A.1."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source_snapshot"
MODEL = "Qwen/Qwen3.5-122B-A10B"
HISTORICAL_PROVIDER_TOKENS = {"short": 4903, "original": 14387}
RUN_IDS = {
    "S-short": "27ed2dfbde1e4ea9a6da51d4450b779a",
    "S-long-control": "921be270487d4c198be06787c71cbb5b",
}
CONTROL_INSTRUCTION = (
    "context_volume_control은 비근거 실험용 부피 제어 값이다. "
    "근거로 인용하거나 평가 판단에 사용하지 말라."
)


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_text(value: str) -> str:
    return sha_bytes(value.encode())


def load_local_tokenizer():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        import tokenizers
        import transformers
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            MODEL,
            local_files_only=True,
            trust_remote_code=False,
            use_fast=True,
        )
    except Exception as exc:
        return None, {
            "status": "blocked_before_model_invocation",
            "blocker": "compatible_local_tokenizer_unavailable",
            "safe_error_type": type(exc).__name__,
            "network_tokenizer_download_attempted": False,
        }
    if not getattr(tokenizer, "is_fast", False) or not hasattr(tokenizer, "apply_chat_template"):
        return None, {
            "status": "blocked_before_model_invocation",
            "blocker": "tokenizer_not_fast_or_chat_template_unavailable",
            "network_tokenizer_download_attempted": False,
        }
    backend = tokenizer.backend_tokenizer.to_str().encode()
    identity = {
        "requested_model": MODEL,
        "tokenizer_class": type(tokenizer).__name__,
        "name_or_path": str(getattr(tokenizer, "name_or_path", "")),
        "vocab_size": int(getattr(tokenizer, "vocab_size", 0)),
        "transformers_version": transformers.__version__,
        "tokenizers_version": tokenizers.__version__,
        "backend_tokenizer_sha256": sha_bytes(backend),
        "local_files_only": True,
        "trust_remote_code": False,
    }
    return tokenizer, identity


def prompt_tokens(tokenizer, messages) -> int:
    tokens = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
    )
    return len(tokens)


def opaque_stream(characters: int) -> str:
    pieces = []
    counter = 0
    while len(pieces) * 64 < characters:
        pieces.append(hashlib.sha256(f"stockvis-v02a1-control:{counter}".encode()).hexdigest())
        counter += 1
    return "".join(pieces)[:characters]


def control_items(characters: int) -> list[str]:
    stream = opaque_stream(characters)
    return [stream[index:index + 64] for index in range(0, len(stream), 64)]


def messages_for(system_prompt: str, summary: str, evidence: list[dict], items: list[str]):
    body = {
        "summary": summary,
        "available_sources": [],
        "provided_documents": evidence,
        "context_volume_control": items,
    }
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": dump(body)}]


def find_exact_control(tokenizer, system_prompt, summary, evidence, target: int):
    def count(characters: int) -> int:
        return prompt_tokens(tokenizer, messages_for(system_prompt, summary, evidence, control_items(characters)))

    low, high = 0, 65536
    while count(high) < target and high < 524288:
        high *= 2
    while low < high:
        middle = (low + high) // 2
        if count(middle) < target:
            low = middle + 1
        else:
            high = middle
    best = (abs(count(low) - target), low, count(low))
    for characters in range(max(0, low - 512), low + 513):
        current = count(characters)
        candidate = (abs(current - target), characters, current)
        if candidate < best:
            best = candidate
        if current == target:
            return characters, current
    return best[1], best[2]


def run_preflight(tokenizer=None, tokenizer_identity=None) -> dict:
    frozen = json.loads((SOURCE / "hard-006.json").read_text())
    short_reference = json.loads((SOURCE / "v02a-sanitized-visible.json").read_text())
    original_reference = json.loads((SOURCE / "v02a-original-visible.json").read_text())
    body = json.loads(short_reference[1]["content"])
    evidence = body["provided_documents"]
    assert len(evidence) == 17 and all(x["kind"] == "evidence" for x in evidence)

    if tokenizer is None:
        tokenizer, tokenizer_identity = load_local_tokenizer()
    if tokenizer is None:
        result = dict(tokenizer_identity)
        result.update({
            "experiment": "Research Evidence Handoff Replay v0.2A.1",
            "model_invocations": 0,
            "historical_artifacts_modified": False,
        })
        return result

    try:
        local_short_reference = prompt_tokens(tokenizer, short_reference)
        local_original_reference = prompt_tokens(tokenizer, original_reference)
    except Exception as exc:
        return {
            "experiment": "Research Evidence Handoff Replay v0.2A.1",
            "status": "blocked_before_model_invocation",
            "blocker": "compatible_chat_template_count_failed",
            "safe_error_type": type(exc).__name__,
            "tokenizer_identity": tokenizer_identity,
            "model_invocations": 0,
        }
    reference_match = {
        "short": {"local": local_short_reference, "provider": HISTORICAL_PROVIDER_TOKENS["short"]},
        "original": {"local": local_original_reference, "provider": HISTORICAL_PROVIDER_TOKENS["original"]},
    }
    if any(row["local"] != row["provider"] for row in reference_match.values()):
        return {
            "experiment": "Research Evidence Handoff Replay v0.2A.1",
            "status": "blocked_before_model_invocation",
            "blocker": "local_tokenizer_does_not_reproduce_provider_reference_counts",
            "tokenizer_identity": tokenizer_identity,
            "reference_counts": reference_match,
            "model_invocations": 0,
        }

    system_prompt = short_reference[0]["content"] + "\n" + CONTROL_INSTRUCTION
    short_messages = messages_for(system_prompt, body["summary"], evidence, [])
    short_tokens = prompt_tokens(tokenizer, short_messages)
    characters, long_tokens = find_exact_control(
        tokenizer, system_prompt, body["summary"], evidence, HISTORICAL_PROVIDER_TOKENS["original"]
    )
    items = control_items(characters)
    long_messages = messages_for(system_prompt, body["summary"], evidence, items)
    payload_text = dump(items)
    allowed = all(set(item) <= set("0123456789abcdef") for item in items)
    if long_tokens != HISTORICAL_PROVIDER_TOKENS["original"] or not allowed:
        return {
            "experiment": "Research Evidence Handoff Replay v0.2A.1",
            "status": "blocked_before_model_invocation",
            "blocker": "exact_token_match_or_opacity_check_failed",
            "tokenizer_identity": tokenizer_identity,
            "reference_counts": reference_match,
            "short_input_tokens": short_tokens,
            "closest_long_input_tokens": long_tokens,
            "control_characters": characters,
            "model_invocations": 0,
        }

    visible = ROOT / "visible"
    visible.mkdir(exist_ok=False)
    arms = {"S-short": short_messages, "S-long-control": long_messages}
    runs = []
    for condition, messages in arms.items():
        run_id = RUN_IDS[condition]
        raw = dump(messages)
        (visible / f"{run_id}.json").write_text(raw)
        runs.append({
            "condition": condition,
            "run_id": run_id,
            "input_sha256": sha_text(raw),
            "local_prompt_tokens": prompt_tokens(tokenizer, messages),
        })
    plan = {
        "experiment": "Research Evidence Handoff Replay v0.2A.1",
        "version": "0.2.1",
        "case": "hard-006",
        "calibration_only": True,
        "independent_variable": "opaque context_volume_control size",
        "historical_context_absent_both_arms": True,
        "historical_target_prompt_tokens": 14387,
        "tokenizer_identity": tokenizer_identity,
        "config": {
            "model": MODEL,
            "temperature": 0.6,
            "top_p": 0.95,
            "seed": 20260909,
            "reasoning": {"enabled": True},
            "max_tokens": 8192,
            "timeout_seconds": 420,
            "retry_count": 0,
        },
        "runs": runs,
    }
    (ROOT / "plan.json").write_text(dump(plan))
    return {
        "experiment": plan["experiment"],
        "status": "ready_for_fixed_execution",
        "model_invocations": 0,
        "tokenizer_identity": tokenizer_identity,
        "reference_counts": reference_match,
        "historical_target_prompt_tokens": 14387,
        "short_input_tokens": short_tokens,
        "long_control_input_tokens": long_tokens,
        "control_payload_item_count": len(items),
        "control_payload_characters": characters,
        "control_payload_sha256": sha_text(payload_text),
        "full_input_sha256": {row["condition"]: row["input_sha256"] for row in runs},
        "integrity": {
            "evidence_count_each_arm": 17,
            "evidence_identical": True,
            "historical_candidate_critique_absent": True,
            "control_hex_only": allowed,
            "protected_expectations_absent": True,
            "model_visible_hard_label_absent": True,
        },
    }


def main() -> int:
    result = run_preflight()
    (ROOT / "preflight_result.json").write_text(dump(result))
    print("PREFLIGHT_STATUS=" + result["status"])
    print("PREFLIGHT_RESULT=" + str(ROOT / "preflight_result.json"))
    return 0 if result["status"] == "ready_for_fixed_execution" else 2


if __name__ == "__main__":
    raise SystemExit(main())
