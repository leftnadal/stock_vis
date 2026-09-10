import json
import unittest

from completion_contract import classify_response


def parse(text):
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("action_not_object")
    return value, "plain_json"


class CompletionContractTests(unittest.TestCase):
    def test_provider_stop_requires_final_protocol(self):
        incomplete = classify_response({
            "status": "complete", "finish_reason": "stop", "returned_model": "m",
            "answer": "unfinished", "usage": {"completion_tokens": 8192},
        }, expected_model="m", requested_max_tokens=8192, parse_action=parse)
        self.assertEqual(incomplete["protocol_completion"], "incomplete")
        complete = classify_response({
            "status": "complete", "finish_reason": "stop", "returned_model": "m",
            "answer": json.dumps({"action": "final", "answer": "ok"}),
            "usage": {"completion_tokens": 10},
        }, expected_model="m", requested_max_tokens=8192, parse_action=parse)
        self.assertEqual(complete["protocol_completion"], "complete")


if __name__ == "__main__":
    unittest.main()
