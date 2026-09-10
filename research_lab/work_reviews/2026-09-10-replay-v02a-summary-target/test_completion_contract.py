import json
import unittest

from completion_contract import classify_response


def parse(text):
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("action_not_object")
    return value, "plain_json"


class CompletionContractTests(unittest.TestCase):
    def test_stop_with_final_is_protocol_complete(self):
        response = {
            "status": "complete", "finish_reason": "stop", "returned_model": "m",
            "answer": json.dumps({"action": "final", "answer": "ok"}),
            "usage": {"completion_tokens": 10},
        }
        got = classify_response(response, expected_model="m", requested_max_tokens=100, parse_action=parse)
        self.assertEqual(got["protocol_completion"], "complete")
        self.assertEqual(got["semantic_review_state"], "pending_semantic_review")

    def test_stop_without_final_is_protocol_failure(self):
        response = {
            "status": "complete", "finish_reason": "stop", "returned_model": "m",
            "answer": "Thinking Process:\n* **Wait, keep considering", 
            "usage": {"completion_tokens": 8192},
        }
        got = classify_response(response, expected_model="m", requested_max_tokens=8192, parse_action=parse)
        self.assertEqual(got["provider_finish_state"], "stop")
        self.assertEqual(got["protocol_completion"], "incomplete")
        self.assertTrue(got["output_budget_fully_used"])
        self.assertTrue(got["reasoning_like_visible_content"])
        self.assertEqual(got["semantic_review_state"], "unassessed")

    def test_retrieve_is_not_final_completion(self):
        response = {
            "status": "complete", "finish_reason": "stop", "returned_model": "m",
            "answer": json.dumps({"action": "retrieve", "source_ids": ["x"]}),
            "usage": {"completion_tokens": 3},
        }
        got = classify_response(response, expected_model="m", requested_max_tokens=10, parse_action=parse)
        self.assertEqual(got["protocol_failure_reason"], "expected_final_action_missing")

    def test_transport_and_model_are_separate(self):
        absent = classify_response(None, expected_model="m", requested_max_tokens=10, parse_action=parse)
        self.assertEqual(absent["transport_status"], "provider_error")
        mismatch = classify_response({"status":"complete","finish_reason":"stop","returned_model":"x","answer":"{}"}, expected_model="m", requested_max_tokens=10, parse_action=parse)
        self.assertEqual(mismatch["protocol_failure_reason"], "model_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
