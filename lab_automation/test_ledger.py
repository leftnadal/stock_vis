from pathlib import Path

from lab_automation.ledger import AppendOnlyLedger, RunEvent


def test_ledger_appends_without_rewrite(tmp_path: Path):
    path = tmp_path / "ledger.jsonl"
    ledger = AppendOnlyLedger(path)

    first = RunEvent(
        job_id="J1",
        run_id="R1",
        stage="intake",
        status="started",
        actor="runner",
        runner_version="0.1",
    )
    second = RunEvent(
        job_id="J1",
        run_id="R1",
        stage="tests",
        status="completed",
        actor="runner",
        runner_version="0.1",
        supersedes_event_id=first.event_id,
    )

    ledger.append(first)
    size_after_first = path.stat().st_size
    ledger.append(second)

    rows = ledger.read_all()
    assert len(rows) == 2
    assert path.stat().st_size > size_after_first
    assert rows[0]["event_id"] == first.event_id
    assert rows[1]["supersedes_event_id"] == first.event_id
