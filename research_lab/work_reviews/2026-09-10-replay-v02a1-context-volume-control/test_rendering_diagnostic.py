from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import rendering_diagnostic as diagnostic


class FakeBatch(dict):
    pass


class FakeTokenizer:
    def __init__(self, *, body=True, wrapped=True, counts=(4903, 14387)):
        self.body = body
        self.wrapped = wrapped
        self.counts = counts
        self.index = 0

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        if not tokenize:
            return "\n".join(x["content"] for x in messages) if self.body else "<|assistant|>"
        count = self.counts[self.index]
        self.index += 1
        return FakeBatch(input_ids=list(range(count)), attention_mask=list(range(count))) \
            if self.wrapped else list(range(count))


def sources(root: Path):
    root.mkdir()
    for filename, suffix in diagnostic.SOURCE_NAMES.items():
        messages = [
            {"role": "system", "content": "system-marker-" + suffix},
            {"role": "user", "content": "user-material-body-" + suffix * 4},
        ]
        (root / suffix).write_text(json.dumps(messages))


class DiagnosticTests(unittest.TestCase):
    def test_top_level_mapping_len_is_not_token_count(self):
        result = diagnostic.inspect_tokenized(FakeBatch(
            input_ids=list(range(4903)), attention_mask=list(range(4903)),
        ))
        self.assertEqual(result["top_level_len"], 2)
        self.assertEqual(result["actual_token_sequence_length"], 4903)
        self.assertTrue(result["top_level_len_differs_from_actual"])

    def test_counting_defect_and_exact_gate_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            sources(root)
            result = diagnostic.diagnose(FakeTokenizer(), root, {"fixed": True})
        self.assertEqual(result["outcome"], "A_counting_defect_confirmed_exact_gate_passed")
        self.assertEqual(result["corrected_exact_count_gate"], "passed")
        self.assertEqual(result["model_provider_invocations"], 0)
        self.assertEqual(result["fixed_experimental_arms_generated"], 0)

    def test_body_omission_stops_before_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            sources(root)
            result = diagnostic.diagnose(FakeTokenizer(body=False), root, {})
        self.assertEqual(result["outcome"], "B_historical_string_body_not_fully_rendered")
        self.assertEqual(result["corrected_exact_count_gate"], "not_rerun")

    def test_plain_sequence_valid_count_mismatch_is_outcome_c(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            sources(root)
            result = diagnostic.diagnose(
                FakeTokenizer(wrapped=False, counts=(100, 200)), root, {},
            )
        self.assertEqual(result["outcome"], "C_valid_local_count_provider_mismatch_remains")
        self.assertEqual(result["corrected_exact_count_gate"], "failed")

    def test_artifact_does_not_persist_rendered_body(self):
        source = Path(diagnostic.__file__).read_text()
        self.assertNotIn('"rendered_text"', source)
        self.assertNotIn("provided_documents", source)


if __name__ == "__main__":
    unittest.main()
