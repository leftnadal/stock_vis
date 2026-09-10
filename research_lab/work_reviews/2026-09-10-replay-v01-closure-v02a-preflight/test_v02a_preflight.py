import unittest
from pathlib import Path
import v02a_preflight


class PreflightTests(unittest.TestCase):
    def test_blocks_without_creating_sanitized_input(self):
        source = Path(__file__).resolve().parent.parent / "research-replay-v01"
        result = v02a_preflight.audit(source)
        self.assertEqual(result["status"], "blocked_before_model_invocation")
        self.assertEqual(result["model_invocations"], 0)
        self.assertEqual(result["preservation_checks"]["evidence_document_count"], 17)
        self.assertTrue(result["candidate_target_audit"]["starts_with_reasoning_marker"])
        self.assertEqual(result["candidate_target_audit"]["explicit_final_answer_markers"], 0)
        self.assertFalse(result["safety"]["sanitized_input_created"])


if __name__ == "__main__":
    unittest.main()
