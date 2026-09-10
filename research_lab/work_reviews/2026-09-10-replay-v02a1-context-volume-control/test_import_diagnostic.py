from __future__ import annotations

import unittest
from pathlib import Path

import diagnose_chat_template_import as diagnostic


class DiagnosticTests(unittest.TestCase):
    def test_module_not_found_identity(self):
        error = ModuleNotFoundError("No module named 'jinja2'", name="jinja2")
        self.assertEqual(diagnostic.candidate_module(error), "jinja2")

    def test_transformers_style_import_error_identity(self):
        error = ImportError("apply_chat_template requires the jinja2 library")
        self.assertEqual(diagnostic.candidate_module(error), "jinja2")

    def test_unrelated_error_does_not_invent_module(self):
        self.assertIsNone(diagnostic.candidate_module(ValueError("bad template")))

    def test_script_contract_forbids_count_and_install(self):
        source = (Path(__file__).resolve().parent / "diagnose_chat_template_import.py").read_text()
        self.assertIn('"historical_count_gate_rerun": False', source)
        self.assertIn('"provider_or_model_invocations": 0', source)
        self.assertNotIn("pip install", source)
        self.assertNotIn("prompt_tokens(", source)


if __name__ == "__main__":
    unittest.main()
