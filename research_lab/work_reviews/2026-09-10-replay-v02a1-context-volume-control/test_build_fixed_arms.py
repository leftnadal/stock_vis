from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import build_fixed_arms as builder


class FakeTokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        body = json.loads(messages[1]["content"])
        characters = sum(len(item) for item in body.get("context_volume_control", []))
        return range(5000 + characters)


class BuildFixedArmsTests(unittest.TestCase):
    def test_build_uses_prior_gate_without_reexecuting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            shutil.copytree(Path(builder.__file__).parent / "source_snapshot", source)
            gate_path = root / "gate.json"
            gate_path.write_text(json.dumps({
                "status": "exact_count_gate_passed",
                "exact_count_gate_execution_count": 1,
                "reference_counts": {
                    "short": {"actual_input_ids_length": 4903, "provider_reference_tokens": 4903,
                              "source_sha256": builder.sha(source / "v02a-sanitized-visible.json")},
                    "original": {"actual_input_ids_length": 14387, "provider_reference_tokens": 14387,
                                 "source_sha256": builder.sha(source / "v02a-original-visible.json")},
                },
            }))
            output = root / "fixed"
            result = builder.build(FakeTokenizer(), {"fixed": True}, source, gate_path, output)
            self.assertEqual(result["status"], "ready_for_two_fixed_calls")
            self.assertFalse(result["prior_gate_reexecuted"])
            self.assertEqual(result["long_control_input_tokens"], 14387)
            plan = json.loads((output / "plan.json").read_text())
            self.assertEqual([row["condition"] for row in plan["runs"]],
                             ["S-short", "S-long-control"])
            self.assertEqual(len(list((output / "visible").glob("*.json"))), 2)
            first = json.loads((output / "visible" / f"{plan['runs'][0]['run_id']}.json").read_text())
            second = json.loads((output / "visible" / f"{plan['runs'][1]['run_id']}.json").read_text())
            self.assertEqual(first[0], second[0])
            a, b = json.loads(first[1]["content"]), json.loads(second[1]["content"])
            for key in ("summary", "available_sources", "provided_documents"):
                self.assertEqual(a[key], b[key])
            self.assertEqual(a["context_volume_control"], [])
            self.assertTrue(b["context_volume_control"])

    def test_builder_does_not_call_provider_or_historical_preflight(self):
        source = Path(builder.__file__).read_text()
        self.assertNotIn("provider_adapter", source)
        self.assertNotIn("run_preflight(", source)
        self.assertNotIn("DEEPINFRA_TOKEN", source)


if __name__ == "__main__":
    unittest.main()
