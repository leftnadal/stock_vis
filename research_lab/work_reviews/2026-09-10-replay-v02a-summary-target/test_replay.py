import json
import hashlib
import unittest
from pathlib import Path

import replay


class ReplayDesignTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((replay.ROOT / "plan.json").read_text())
        self.diff = json.loads((replay.ROOT / "input_diff.json").read_text())

    def test_exact_two_opaque_runs_and_frozen_config(self):
        self.assertEqual([x["condition"] for x in self.plan["runs"]], ["original", "sanitized"])
        self.assertEqual(len({x["run_id"] for x in self.plan["runs"]}), 2)
        self.assertTrue(all("hard-006" not in x["run_id"] for x in self.plan["runs"]))
        self.assertEqual(self.plan["config"]["retry_count"], 0)
        self.assertEqual(self.plan["config"]["max_tokens"], 8192)

    def test_visible_input_hashes_match_plan(self):
        for spec in self.plan["runs"]:
            raw = (replay.ROOT / "visible" / f"{spec['run_id']}.json").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), spec["input_sha256"])

    def test_only_historical_context_differs(self):
        bodies = []
        prompts = []
        for spec in self.plan["runs"]:
            messages = json.loads((replay.ROOT / "visible" / f"{spec['run_id']}.json").read_text())
            prompts.append(messages[0])
            bodies.append(json.loads(messages[1]["content"]))
        self.assertEqual(prompts[0], prompts[1])
        self.assertEqual(bodies[0]["summary"], bodies[1]["summary"])
        original_evidence = [x for x in bodies[0]["provided_documents"] if x["kind"] == "evidence"]
        sanitized_evidence = bodies[1]["provided_documents"]
        self.assertEqual(original_evidence, sanitized_evidence)
        self.assertEqual(len(original_evidence), 17)
        removed = [x for x in bodies[0]["provided_documents"] if x["kind"] == "candidate_output"]
        self.assertEqual(len(removed), 2)
        self.assertFalse(any(x["kind"] == "candidate_output" for x in bodies[1]["provided_documents"]))

    def test_no_answer_key_or_expected_ids(self):
        for spec in self.plan["runs"]:
            raw = (replay.ROOT / "visible" / f"{spec['run_id']}.json").read_text()
            self.assertNotIn("protected_expectations", raw)
            self.assertNotIn("expected_evidence", raw)
            self.assertNotIn(spec["condition"], raw)
        self.assertFalse(self.diff["answer_key_guidance_added"])
        self.assertEqual(self.diff["added_or_emphasized_evidence"], [])

    def test_summary_is_the_declared_target_not_reconstructed_answer(self):
        self.assertEqual(self.plan["evaluation_target"]["kind"], "frozen_summary")
        self.assertIn("not a reconstructed", self.plan["evaluation_target"]["identity_note"])


if __name__ == "__main__":
    unittest.main()
