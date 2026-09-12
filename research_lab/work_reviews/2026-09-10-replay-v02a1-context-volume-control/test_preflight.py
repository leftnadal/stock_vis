import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import preflight


class FakeTokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        body = json.loads(messages[1]["content"])
        if "context_volume_control" not in body:
            historical = sum(x["kind"] == "candidate_output" for x in body["provided_documents"])
            return range(14387 if historical else 4903)
        characters = sum(len(x) for x in body["context_volume_control"])
        return range(5000 + characters)


class FakeBatchEncoding(dict):
    pass


class PreflightTests(unittest.TestCase):
    def test_prompt_tokens_uses_input_ids_not_mapping_key_count(self):
        tokenizer = mock.Mock()
        tokenizer.apply_chat_template.return_value = FakeBatchEncoding(
            input_ids=list(range(4903)), attention_mask=list(range(4903)),
        )
        self.assertEqual(preflight.prompt_tokens(tokenizer, []), 4903)
        self.assertEqual(len(tokenizer.apply_chat_template.return_value), 2)

    def test_opaque_control_is_deterministic_hex(self):
        first = preflight.control_items(257)
        self.assertEqual(first, preflight.control_items(257))
        self.assertEqual(sum(map(len, first)), 257)
        self.assertTrue(all(set(item) <= set("0123456789abcdef") for item in first))

    def test_unavailable_tokenizer_blocks_before_input_build(self):
        with mock.patch.object(preflight, "load_local_tokenizer", return_value=(None, {
            "status": "blocked_before_model_invocation", "blocker": "compatible_local_tokenizer_unavailable"
        })):
            result = preflight.run_preflight()
        self.assertEqual(result["status"], "blocked_before_model_invocation")
        self.assertEqual(result["model_invocations"], 0)

    def test_exact_reference_and_target_builds_two_clean_arms(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(preflight.SOURCE, root / "source_snapshot")
            with mock.patch.object(preflight, "ROOT", root), mock.patch.object(preflight, "SOURCE", root / "source_snapshot"):
                result = preflight.run_preflight(FakeTokenizer(), {"tokenizer_class": "FakeExactTokenizer"})
                self.assertEqual(result["status"], "ready_for_fixed_execution")
                self.assertEqual(result["long_control_input_tokens"], 14387)
                self.assertEqual(result["short_input_tokens"], 5000)
                plan = json.loads((root / "plan.json").read_text())
                self.assertEqual(len(plan["runs"]), 2)
                for row in plan["runs"]:
                    visible = (root / "visible" / f"{row['run_id']}.json").read_text()
                    self.assertNotIn("hard-006", visible)
                    body = json.loads(json.loads(visible)[1]["content"])
                    self.assertTrue(all(x["kind"] == "evidence" for x in body["provided_documents"]))


if __name__ == "__main__":
    unittest.main()
