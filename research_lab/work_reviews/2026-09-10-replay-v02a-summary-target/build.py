"""Build the approved summary-target C-original/C-sanitized calibration inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source_snapshot"
OPAQUE_RUN_IDS = {
    "original": "7d7d0d48e6de4c328ff5ff71d600c23c",
    "sanitized": "aadf9a4e2c884b1387fb6e83fa8a35ef",
}


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    frozen = json.loads((SOURCE / "hard-006.json").read_text())
    original_messages = json.loads((SOURCE / "original_c_visible.json").read_text())
    original_body = json.loads(original_messages[1]["content"])
    evidence = [x for x in original_body["provided_documents"] if x["kind"] == "evidence"]
    historical = [x for x in original_body["provided_documents"] if x["kind"] == "candidate_output"]
    assert len(evidence) == 17 and len(historical) == 2
    assert original_body["summary"] == frozen["summary"]

    plan = {
        "experiment": "Research Evidence Handoff Replay v0.2A",
        "version": "0.2.0",
        "purpose": "summary-target full-context contamination isolation",
        "case": "hard-006",
        "calibration_only": True,
        "independent_variable": "historical candidate/critique context presence",
        "evaluation_target": {
            "kind": "frozen_summary",
            "sha256": sha_text(frozen["summary"]),
            "identity_note": "Identical frozen v0.1 summary in both arms; not a reconstructed historical final answer.",
        },
        "config": {
            "model": "Qwen/Qwen3.5-122B-A10B",
            "temperature": 0.6,
            "top_p": 0.95,
            "seed": 20260909,
            "reasoning": {"enabled": True},
            "max_tokens": 8192,
            "timeout_seconds": 420,
            "retry_count": 0,
            "max_calls_per_run": 3,
        },
        "runs": [],
        "interpretation_limits": [
            "Exposed calibration case; not held-out evidence.",
            "No permanent architecture, role, memory, model residency or methodology inference.",
            "Historical v0.1 C failure is a comparator, not a rerun target.",
            "This experiment isolates historical-context presence, not evidence selection.",
        ],
    }
    visible = ROOT / "visible"
    visible.mkdir(exist_ok=True)
    variants = {
        "original": evidence + historical,
        "sanitized": evidence,
    }
    for condition, documents in variants.items():
        body = {
            "summary": frozen["summary"],
            "available_sources": [],
            "provided_documents": documents,
        }
        messages = [original_messages[0], {"role": "user", "content": dump(body)}]
        run_id = OPAQUE_RUN_IDS[condition]
        (visible / f"{run_id}.json").write_text(dump(messages))
        plan["runs"].append({
            "run_id": run_id,
            "condition": condition,
            "input_sha256": sha_text(dump(messages)),
            "summary_sha256": sha_text(frozen["summary"]),
            "evidence_document_sha256": [sha_text(dump(x)) for x in evidence],
            "historical_context_sha256": [sha_text(dump(x)) for x in documents if x["kind"] == "candidate_output"],
        })
    (ROOT / "plan.json").write_text(dump(plan))
    diff = {
        "comparison": "original minus sanitized",
        "unchanged": {
            "system_prompt_sha256": sha_text(original_messages[0]["content"]),
            "summary_sha256": sha_text(frozen["summary"]),
            "evidence_document_count": len(evidence),
            "evidence_document_sha256": [sha_text(dump(x)) for x in evidence],
            "evidence_order_preserved": True,
            "model_and_generation_config": plan["config"],
        },
        "removed_from_sanitized": [
            {"source_id": x["source_id"], "kind": x["kind"], "sha256": sha_text(dump(x)), "content_in_diff": False}
            for x in historical
        ],
        "added_or_emphasized_evidence": [],
        "answer_key_guidance_added": False,
        "expected_evidence_ids_exposed": False,
    }
    (ROOT / "input_diff.json").write_text(dump(diff))


if __name__ == "__main__":
    main()
