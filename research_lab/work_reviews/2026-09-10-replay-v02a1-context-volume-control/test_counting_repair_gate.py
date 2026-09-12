from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import counting_repair_gate as gate


class FakeBatch(dict):
    pass


class FakeTokenizer:
    def __init__(self, counts=(4903, 14387)):
        self.counts = iter(counts)

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        count = next(self.counts)
        return FakeBatch(input_ids=list(range(count)), attention_mask=list(range(count)))


class CountingRepairGateTests(unittest.TestCase):
    def sources(self, root: Path):
        root.mkdir()
        for filename, _ in gate.REFERENCES.values():
            (root / filename).write_text(json.dumps([
                {"role": "system", "content": "system"},
                {"role": "user", "content": filename},
            ]))

    def test_exact_gate_passes_using_actual_input_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            self.sources(root)
            result = gate.run_gate(FakeTokenizer(), root, {"fixed": True})
        self.assertEqual(result["status"], "exact_count_gate_passed")
        self.assertEqual(result["reference_counts"]["short"]["legacy_top_level_len"], 2)
        self.assertEqual(result["reference_counts"]["short"]["actual_input_ids_length"], 4903)
        self.assertEqual(result["exact_count_gate_execution_count"], 1)
        self.assertEqual(result["model_visible_arms_generated"], 0)
        self.assertEqual(result["provider_model_invocations"], 0)

    def test_mismatch_fails_without_arm_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            self.sources(root)
            result = gate.run_gate(FakeTokenizer((100, 200)), root, {})
        self.assertEqual(result["status"], "exact_count_gate_failed")
        self.assertEqual(result["model_visible_arms_generated"], 0)

    def test_gate_source_does_not_build_or_execute_arms(self):
        source = Path(gate.__file__).read_text()
        for forbidden in ("messages_for(", "find_exact_control(", "provider_adapter", "DEEPINFRA_TOKEN"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
