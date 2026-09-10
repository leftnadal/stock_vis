from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import execute_jinja_correction_and_continue as launcher
import jinja_correction_contract as contract


class JinjaCorrectionTests(unittest.TestCase):
    def test_download_is_exact_two_pin_official_binary_no_deps(self):
        command = contract.download_command(Path("/venv/python"), Path("/wheels"))
        self.assertIn("https://pypi.org/simple", command)
        self.assertIn("Jinja2==3.1.6", command)
        self.assertIn("MarkupSafe==3.0.2", command)
        self.assertIn("--only-binary=:all:", command)
        self.assertIn("--no-deps", command)
        self.assertNotIn("transformers==5.16.1", command)

    def test_install_reuses_original_wheels_and_has_no_index(self):
        command = contract.install_command(
            Path("/venv/python"), Path("/original"), Path("/correction"),
        )
        self.assertIn("--no-index", command)
        self.assertEqual(command.count("--find-links"), 2)
        for pin in (
            "transformers==5.16.1", "tokenizers==0.23.2",
            "Jinja2==3.1.6", "MarkupSafe==3.0.2",
        ):
            self.assertIn(pin, command)

    def test_original_artifact_identity_and_hash_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            item = artifacts / "one.whl"
            item.write_bytes(b"fixed")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"rows": [{
                "filename": "one.whl", "bytes": 5,
                "sha256": contract.sha256_file(item),
            }]}))
            verified = contract.verify_original_files(manifest, artifacts, "rows")
            self.assertEqual(verified[0]["filename"], "one.whl")
            item.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "integrity_mismatch"):
                contract.verify_original_files(manifest, artifacts, "rows")

    def test_freeze_is_original_plus_exact_correction_only(self):
        original = ["pip==24.0", "transformers==5.16.1", "tokenizers==0.23.2"]
        corrected = original + ["Jinja2==3.1.6", "MarkupSafe==3.0.2"]
        contract.verify_freeze("\n".join(corrected), original)
        with self.assertRaisesRegex(ValueError, "freeze_mismatch"):
            contract.verify_freeze("\n".join(corrected + ["other==1"]), original)

    def test_runner_keeps_gate_and_execution_checksums_separate(self):
        text = Path(launcher.__file__).read_text()
        self.assertIn("GATE_SHA256SUMS", text)
        self.assertIn("EXECUTION_SHA256SUMS", text)
        self.assertIn("EXECUTION_BLOCKER_SHA256SUMS", text)
        self.assertIn("append_only_staged_scope_violation", text)
        self.assertIn('"model_run_limit": 2', text)
        self.assertIn('"retries": 0', text)


if __name__ == "__main__":
    unittest.main()
