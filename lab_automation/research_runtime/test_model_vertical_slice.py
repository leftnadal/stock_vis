from pathlib import Path
import json
import sys

from lab_automation.research_runtime.model_vertical_slice import run_model_vertical_slice


def test_model_vertical_slice_with_fake_command_backend(tmp_path: Path):
    responder = tmp_path / "responder.py"
    responder.write_text(
        "import json, os\n"
        "role = os.environ['STOCKVIS_RESEARCH_ROLE']\n"
        "outputs = {\n"
        "  'researcher': {\n"
        "    'claims': {'segment_a_total_share': 0.60, 'customer_z_total_share': 0.40},\n"
        "    'reasoning_summary': 'baseline',\n"
        "    'uncertainty': []\n"
        "  },\n"
        "  'critic': {\n"
        "    'findings': [\n"
        "      {'type': 'repair', 'target': 'customer_z_total_share', 'message': 'denominator mismatch'},\n"
        "      {'type': 'preserve', 'target': 'segment_a_total_share', 'message': 'supported'}\n"
        "    ],\n"
        "    'proposed_revision': {'claims': {'segment_a_total_share': 0.60, 'customer_z_total_share': 0.24}}\n"
        "  },\n"
        "  'revision': {\n"
        "    'claims': {'segment_a_total_share': 0.60, 'customer_z_total_share': 0.24},\n"
        "    'conditions': [],\n"
        "    'uncertainty': []\n"
        "  },\n"
        "  'evaluator': {\n"
        "    'repaired_errors': ['customer_z_total_share denominator mismatch'],\n"
        "    'preserved_correct_content': ['segment_a_total_share'],\n"
        "    'introduced_errors': [],\n"
        "    'unresolved_errors': [],\n"
        "    'conclusion': 'improved'\n"
        "  }\n"
        "}\n"
        "print(json.dumps(outputs[role]))\n",
        encoding="utf-8",
    )
    config = tmp_path / "backend.json"
    config.write_text(
        json.dumps(
            {
                "backend_type": "command_json",
                "default": {
                    "command": [sys.executable, str(responder)],
                    "backend_name": "fake_command",
                    "requested_identity": "fake/model-v0.1",
                    "identity_assurance": "artifact_verified",
                    "timeout_seconds": 10,
                },
                "roles": {},
            }
        ),
        encoding="utf-8",
    )

    summary = run_model_vertical_slice(config, tmp_path / "state")

    assert summary["status"] == "completed"
    assert summary["blocking_failures"] == []
    assert summary["benchmark"]["net_direction"] == "improved"
    assert summary["benchmark"]["introduced_errors"] == []
    assert summary["benchmark"]["unresolved_errors"] == []
    separation = [
        row
        for row in summary["integrity_findings"]
        if row["code"] == "evaluator_critic_reasoning_separation"
    ][0]
    assert separation["status"] == "PASS"


def test_model_vertical_slice_fails_closed_on_invalid_json(tmp_path: Path):
    responder = tmp_path / "bad.py"
    responder.write_text("print('not json')\n", encoding="utf-8")
    config = tmp_path / "backend.json"
    config.write_text(
        json.dumps(
            {
                "backend_type": "command_json",
                "default": {"command": [sys.executable, str(responder)]},
                "roles": {},
            }
        ),
        encoding="utf-8",
    )

    try:
        run_model_vertical_slice(config, tmp_path / "state")
    except RuntimeError as exc:
        assert "valid JSON object" in str(exc)
    else:
        raise AssertionError("invalid model output must fail closed")
