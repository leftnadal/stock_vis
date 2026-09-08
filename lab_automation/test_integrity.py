from pathlib import Path

from lab_automation.integrity import require_output_contract, validate_json_artifact


def test_output_contract_requires_all_three_executor_artifacts():
    finding = require_output_contract(
        {
            "agent_report.md": "agent_generated",
            "result.json": "agent_generated",
            "data_gaps.json": "missing",
        },
        ("agent_report.md", "result.json", "data_gaps.json"),
    )

    assert finding.status == "FAIL"
    assert "data_gaps.json" in finding.message


def test_json_artifact_rejects_invalid_json(tmp_path: Path):
    path = tmp_path / "result.json"
    path.write_text("not-json\n", encoding="utf-8")

    finding = validate_json_artifact(path)

    assert finding.status == "FAIL"
    assert "invalid JSON" in finding.message


def test_result_json_rejects_empty_object(tmp_path: Path):
    path = tmp_path / "result.json"
    path.write_text("{}\n", encoding="utf-8")

    finding = validate_json_artifact(path, reject_empty_object=True)

    assert finding.status == "FAIL"
    assert "empty JSON object" in finding.message


def test_data_gaps_json_accepts_empty_array(tmp_path: Path):
    path = tmp_path / "data_gaps.json"
    path.write_text("[]\n", encoding="utf-8")

    finding = validate_json_artifact(path)

    assert finding.status == "PASS"
