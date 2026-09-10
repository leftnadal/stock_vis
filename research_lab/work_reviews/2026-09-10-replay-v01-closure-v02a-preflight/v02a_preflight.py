"""Build no model input. Audit whether a sanctioned sanitized target can be formed."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def audit(source_root: Path) -> dict:
    frozen_path = source_root / "frozen" / "hard-006.json"
    frozen_raw = frozen_path.read_bytes()
    frozen = json.loads(frozen_raw)
    evidence = [d for d in frozen["documents"].values() if d["kind"] == "evidence"]
    candidates = [d for d in frozen["documents"].values() if d["kind"] == "candidate_output"]
    primary = next(d for d in candidates if d["source_id"] == "428c01c2bc7343f299088eccb8ab09d3")
    text = primary["fragment"]
    starts_reasoning = text.startswith("Thinking Process:")
    final_markers = list(re.finditer(r"(?:^|\n)(?:Final Answer|최종 답변)\s*:?", text, re.I))
    evidence_hashes = {d["source_id"]: sha_bytes(json.dumps(d, ensure_ascii=False, sort_keys=True).encode()) for d in evidence}
    return {
        "experiment": "Research Evidence Handoff Replay v0.2A",
        "case": "hard-006",
        "status": "blocked_before_model_invocation",
        "model_invocations": 0,
        "research_question": "Does removal of historical instruction/reasoning residue change protocol completion and semantic behavior under full evidence context?",
        "planned_independent_variable": "historical_context_sanitization",
        "preservation_checks": {
            "evidence_document_count": len(evidence),
            "evidence_bodies_planned_byte_equivalent": True,
            "evidence_document_hashes": evidence_hashes,
            "frozen_source_sha256": sha_bytes(frozen_raw),
            "candidate_source_id": primary["source_id"],
            "candidate_source_sha256": primary["sha256"],
            "candidate_answer_sha256": frozen["candidate_refs"][0]["answer_sha256"],
        },
        "candidate_target_audit": {
            "fragment_characters": len(text),
            "starts_with_reasoning_marker": starts_reasoning,
            "explicit_final_answer_markers": len(final_markers),
            "source_ends_without_final_answer": not final_markers,
        },
        "blocker": "candidate_answer_not_separable_from_reasoning_like_historical_output",
        "why_blocked": "Removing the entire primary fragment would violate candidate-answer identity preservation; extracting or synthesizing a target would change more than the approved sanitization variable.",
        "decision_needed": [
            "Use the frozen summary as the evaluation target and treat both historical candidate outputs only as removable context",
            "Use a provenance-linked excerpt from the critic's corrected research result as a new derived candidate target",
            "Supply a separately attested historical final candidate answer if one exists",
        ],
        "safety": {"provider_called": False, "historical_artifact_modified": False, "sanitized_input_created": False},
    }


if __name__ == "__main__":
    source = HERE.parent / "research-replay-v01"
    result = audit(source)
    output = HERE / "v02a_preflight_result.json"
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(output)
