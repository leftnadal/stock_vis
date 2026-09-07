import json
from pathlib import Path

from lab_automation.research_runtime.vertical_slice import (
    EXPERIMENT_ID,
    run_vertical_slice,
)


def test_vertical_slice_completes_with_reconstructable_critic_delta(
    tmp_path: Path,
):
    result = run_vertical_slice(tmp_path)

    assert result["status"] == "completed"
    assert result["blocking_failures"] == []
    assert result["evaluation"]["conclusion"] == "improved"
    assert result["evaluation"]["repaired_errors"] == [
        "customer_z_total_share denominator mismatch"
    ]
    assert result["evaluation"]["preserved_correct_content"] == [
        "segment_a_total_share"
    ]
    assert result["evaluation"]["introduced_errors"] == []
    assert result["evaluation"]["unresolved_errors"] == []
    assert result["evaluator_exposed_to_critic"] is False

    assert all(
        finding["status"] != "FAIL"
        for finding in result["integrity_findings"]
    )
    assert result["profile_ref"].startswith("artifact://sha256/")
    assert result["evaluation_ref"].startswith("artifact://sha256/")
    assert result["summary_ref"].startswith("artifact://sha256/")

    summary_path = Path(result["summary_path"])
    assert summary_path.is_file()
    persisted = json.loads(summary_path.read_text(encoding="utf-8"))
    assert persisted["execution_id"] == result["execution_id"]

    ledger_path = (
        tmp_path
        / "ledger"
        / f"{EXPERIMENT_ID}-{result['execution_id']}.jsonl"
    )
    rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [row["stage"] for row in rows] == [
        "researcher",
        "critic",
        "revision",
        "evaluator",
        "research_experiment_complete",
    ]
    for row in rows:
        for artifact_ref in row["artifact_refs"]:
            assert artifact_ref.startswith("artifact://sha256/")


def test_vertical_slice_repeated_runs_do_not_overwrite_runtime_history(
    tmp_path: Path,
):
    first = run_vertical_slice(tmp_path)
    second = run_vertical_slice(tmp_path)

    assert first["execution_id"] != second["execution_id"]
    assert Path(first["summary_path"]).is_file()
    assert Path(second["summary_path"]).is_file()
    assert Path(first["summary_path"]) != Path(second["summary_path"])
