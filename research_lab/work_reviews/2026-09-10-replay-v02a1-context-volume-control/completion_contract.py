"""Experiment-local completion classification. It does not infer semantic quality."""
from __future__ import annotations

import re
from typing import Any, Callable


REASONING_LIKE = re.compile(
    r"(?:^|\n)\s*(?:Thinking Process:|\*\s*\*\*Wait,|\d+\.\s+\*\*Analyze the Request)",
    re.IGNORECASE,
)


def classify_response(
    response: dict[str, Any] | None,
    *,
    expected_model: str,
    requested_max_tokens: int,
    parse_action: Callable[[str], tuple[dict[str, Any], str]],
) -> dict[str, Any]:
    """Separate transport, provider, protocol, visible-content and semantic states."""
    if response is None:
        return {
            "transport_status": "provider_error",
            "provider_finish_state": "unavailable",
            "protocol_completion": "not_assessed",
            "protocol_failure_reason": "no_response",
            "semantic_review_state": "unassessed",
            "visible_content_state": "absent",
        }

    answer = response.get("answer")
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    completion_tokens = usage.get("completion_tokens")
    result = {
        "transport_status": "response_received",
        "provider_finish_state": response.get("finish_reason", "other"),
        "provider_status": response.get("status", "unknown"),
        "model_identity_match": response.get("returned_model") == expected_model,
        "protocol_completion": "incomplete",
        "protocol_failure_reason": None,
        "semantic_review_state": "unassessed",
        "visible_content_state": "absent" if not isinstance(answer, str) or not answer else "present",
        "reasoning_like_visible_content": bool(isinstance(answer, str) and REASONING_LIKE.search(answer)),
        "output_budget_fully_used": type(completion_tokens) is int and completion_tokens >= requested_max_tokens,
    }
    if response.get("status") != "complete":
        result["protocol_failure_reason"] = "provider_response_not_complete"
        return result
    if not result["model_identity_match"]:
        result["protocol_failure_reason"] = "model_identity_mismatch"
        return result
    if not isinstance(answer, str) or not answer.strip():
        result["protocol_failure_reason"] = "answer_missing"
        return result
    try:
        action, wrapping = parse_action(answer)
    except (ValueError, TypeError, KeyError) as exc:
        result["protocol_failure_reason"] = type(exc).__name__
        result["protocol_parse_error_code"] = str(exc)
        return result
    result["response_wrapping"] = wrapping
    if action.get("action") != "final":
        result["protocol_failure_reason"] = "expected_final_action_missing"
        return result
    result["protocol_completion"] = "complete"
    result["protocol_failure_reason"] = None
    result["semantic_review_state"] = "pending_semantic_review"
    return result

