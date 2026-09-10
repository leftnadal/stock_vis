from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import acquisition_contract as contract
import acquire_once_and_continue as launcher
import acquired_preflight


class AcquisitionContractTests(unittest.TestCase):
    def test_pip_commands_have_exact_pins_and_official_index(self):
        download = contract.pip_download_command(Path("/isolated/python"), Path("/wheels"))
        install = contract.pip_install_command(Path("/isolated/python"), Path("/wheels"))
        self.assertIn("https://pypi.org/simple", download)
        self.assertIn("transformers==5.16.1", download)
        self.assertIn("tokenizers==0.23.2", download)
        self.assertIn("--only-binary=:all:", download)
        self.assertIn("--no-index", install)
        self.assertNotIn("--index-url", install)

    def test_asset_selection_is_minimum_allowlist(self):
        selected = contract.select_tokenizer_assets([
            "tokenizer.json", "tokenizer_config.json", "config.json",
            "model-00001-of-00099.safetensors", "README.md",
        ])
        self.assertEqual(selected, ["config.json", "tokenizer.json", "tokenizer_config.json"])

    def test_required_assets_and_immutable_revision_enforced(self):
        with self.assertRaisesRegex(ValueError, "required_tokenizer_assets_missing"):
            contract.select_tokenizer_assets(["tokenizer_config.json"])
        with self.assertRaisesRegex(ValueError, "immutable_revision_unavailable"):
            contract.validate_revision("main")
        contract.validate_revision("a" * 40)

    def test_downloaded_asset_hashes_and_size_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tokenizer.json").write_text("{}")
            rows = contract.validate_downloaded_assets(root, ["tokenizer.json"])
            self.assertEqual(rows[0]["bytes"], 2)
            self.assertEqual(len(rows[0]["sha256"]), 64)

    def test_installed_direct_pins_are_exact(self):
        launcher.verify_installed_pins("transformers==5.16.1\ntokenizers==0.23.2\n")
        with self.assertRaisesRegex(ValueError, "pin_mismatch"):
            launcher.verify_installed_pins("transformers==5.16.0\ntokenizers==0.23.2\n")

    def test_replay_root_is_externalizable_without_changing_script_root(self):
        text = (Path(__file__).resolve().parent / "replay.py").read_text()
        self.assertIn('REPLAY_EXPERIMENT_ROOT', text)
        self.assertIn('SCRIPT_ROOT.parents[3] / ".env"', text)

    def test_input_diff_accepts_only_empty_vs_opaque_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            visible = root / "visible"
            visible.mkdir()
            system = {"role": "system", "content": "fixed"}
            base = {
                "summary": "frozen", "available_sources": [],
                "provided_documents": [{"kind": "evidence", "content": "same"}],
                "context_volume_control": [],
            }
            long = dict(base)
            long["context_volume_control"] = ["a" * 64]
            (visible / "s.json").write_text(contract_json([system, {"role": "user", "content": contract_json(base)}]))
            (visible / "l.json").write_text(contract_json([system, {"role": "user", "content": contract_json(long)}]))
            (root / "plan.json").write_text(contract_json({"runs": [
                {"condition": "S-short", "run_id": "s"},
                {"condition": "S-long-control", "run_id": "l"},
            ]}))
            result = acquired_preflight.verify_and_record_input_diff(root)
            self.assertEqual(result["only_differing_field"], "context_volume_control")
            self.assertTrue((root / "input_diff_and_leakage.json").exists())


def contract_json(value):
    import json
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
