from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import replay_fixed_once as replay


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def setup_root(root: Path):
    runs = []
    for index, condition in enumerate(replay.EXPECTED_CONDITIONS):
        run_id = f"{index + 1:032x}"
        messages = [{"role": "system", "content": "fixed"}, {"role": "user", "content": condition}]
        raw = json.dumps(messages, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        (root / "visible").mkdir(exist_ok=True)
        (root / "visible" / f"{run_id}.json").write_text(raw)
        runs.append({
            "run_id": run_id,
            "condition": condition,
            "input_sha256": replay.sha_bytes(raw.encode()),
            "local_prompt_tokens": 100 + index,
        })
    write(root / "plan.json", {
        "experiment": "test", "case": "hard-006", "runs": runs,
        "config": {"model": "m", "temperature": 0.6, "top_p": 0.95,
                   "seed": 20260909, "reasoning": {"enabled": True},
                   "timeout_seconds": 420},
    })


def response(answer: str, prompt_tokens: int, model="m"):
    return {"status": "complete", "finish_reason": "stop", "returned_model": model,
            "answer": answer, "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": 10}}


class FixedReplayTests(unittest.TestCase):
    def run_with(self, responses):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            setup_root(root)
            calls = iter(responses)
            with mock.patch.object(replay, "ROOT", root), \
                 mock.patch.object(replay.provider, "sanitize_response", side_effect=lambda raw, *_: raw):
                code = replay.execute(post_json=lambda *_: next(calls), token="synthetic")
            batch = next((root / "executions").iterdir())
            ledger = json.loads((batch / "manifest.json").read_text())
            results = [json.loads(path.read_text()) for path in sorted(batch.glob("*/result.json"))]
            return code, ledger, results

    def test_protocol_failure_does_not_cancel_second_arm(self):
        code, ledger, results = self.run_with([
            response("not-json", 100),
            response(json.dumps({"action": "final", "answer": "ok", "used_source_ids": [],
                                 "changes": [], "limitations": []}), 101),
        ])
        self.assertEqual(code, 0)
        self.assertEqual(ledger["model_invocations"], 2)
        self.assertEqual(ledger["status"], "execution_finished_pending_review")
        self.assertEqual(len(results), 2)

    def test_prompt_accounting_mismatch_stops_before_second_arm(self):
        code, ledger, results = self.run_with([response("not-json", 999)])
        self.assertEqual(code, 0)
        self.assertEqual(ledger["model_invocations"], 1)
        self.assertEqual(ledger["status"], "safety_stopped_pending_review")
        self.assertEqual(ledger["safety_stop_reason"], "provider_local_prompt_token_mismatch")
        self.assertEqual(len(results), 1)

    def test_model_mismatch_stops_before_second_arm(self):
        _, ledger, _ = self.run_with([response("not-json", 100, model="different")])
        self.assertEqual(ledger["model_invocations"], 1)
        self.assertEqual(ledger["safety_stop_reason"], "model_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
