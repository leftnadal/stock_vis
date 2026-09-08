import json
from pathlib import Path
import sys

import pytest

import lab_automation.issue_queue as issue_queue_module
from lab_automation.issue_queue import materialize_job, parse_job_body, validate_queue_issue


BODY = '''
# Job
```yaml
job_id: SV-TEST-001
lab: math_lab
status: queued
branch: math-lab/data-eligibility-v0.1
goal: test queue intake
execution:
  db_access: read_only
  network_policy: restricted
  destructive_actions_allowed: false
authority_refs:
  - math_lab/00_foundation/foundation_ko.md
allowed_write_paths:
  - math_lab
expected_outputs:
  - report
promotion:
  push: requires_ceo_approval
```
'''


def issue():
    return {
        "number": 34,
        "title": "queued test",
        "body": BODY,
        "url": "https://github.com/leftnadal/stock_vis/issues/34",
        "labels": [{"name": "lab-automation"}, {"name": "queued"}],
    }


def running_issue():
    value = issue()
    value["state"] = "OPEN"
    value["labels"] = [{"name": "lab-automation"}, {"name": "running"}]
    return value


def write_claim(state_root: Path, *, job_id: str = "SV-TEST-001") -> Path:
    path = state_root / "claims" / "issue-34.claim"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"issue_number": 34, "job_id": job_id}),
        encoding="utf-8",
    )
    return path


def test_parse_job_body_flattens_execution_contract():
    raw = parse_job_body(BODY)
    assert raw["job_id"] == "SV-TEST-001"
    assert raw["db_access"] == "read_only"
    assert raw["network_policy"] == "restricted"
    assert raw["destructive_actions_allowed"] is False
    assert raw["promotion"]["push"] == "requires_ceo_approval"


def test_validate_queue_issue_requires_labels():
    bad = issue()
    bad["labels"] = [{"name": "lab-automation"}]
    with pytest.raises(ValueError):
        validate_queue_issue(bad)


def test_materialize_job_creates_claim_and_json(tmp_path: Path):
    path = materialize_job(issue(), tmp_path)
    payload = json.loads(path.read_text())
    assert payload["source_issue_number"] == 34
    assert payload["db_access"] == "read_only"
    assert (tmp_path / "claims" / "issue-34.claim").exists()


def test_materialize_job_rejects_duplicate_local_claim(tmp_path: Path):
    materialize_job(issue(), tmp_path)
    with pytest.raises(RuntimeError):
        materialize_job(issue(), tmp_path)


@pytest.mark.parametrize(
    "labels",
    [
        ["lab-automation", "queued"],
        ["lab-automation", "queued", "running"],
        ["lab-automation", "running", "failed"],
        ["running"],
    ],
)
def test_running_resume_rejects_any_non_running_queue_state(labels):
    candidate = running_issue()
    candidate["labels"] = [{"name": name} for name in labels]

    with pytest.raises(ValueError):
        issue_queue_module.validate_running_issue(candidate)


def test_running_resume_rematerializes_only_job_from_matching_claim(tmp_path: Path):
    claim_path = write_claim(tmp_path)
    original_claim = claim_path.read_bytes()
    original_mtime = claim_path.stat().st_mtime_ns

    job_path = issue_queue_module.rematerialize_running_job(
        running_issue(),
        tmp_path,
    )
    second_path = issue_queue_module.rematerialize_running_job(
        running_issue(),
        tmp_path,
    )

    assert second_path == job_path
    assert json.loads(job_path.read_text())["source_issue_number"] == 34
    assert claim_path.read_bytes() == original_claim
    assert claim_path.stat().st_mtime_ns == original_mtime


def test_running_resume_requires_matching_existing_claim(tmp_path: Path):
    write_claim(tmp_path, job_id="OTHER-JOB")

    with pytest.raises(RuntimeError, match="does not match running issue"):
        issue_queue_module.rematerialize_running_job(running_issue(), tmp_path)


def test_running_resume_refuses_to_overwrite_different_job(tmp_path: Path):
    write_claim(tmp_path)
    job_path = tmp_path / "jobs" / "SV-TEST-001.json"
    job_path.parent.mkdir()
    job_path.write_text('{"different": true}\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="refuses to overwrite"):
        issue_queue_module.rematerialize_running_job(running_issue(), tmp_path)


def test_resume_cli_bypasses_queued_selection_and_label_mutation(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    write_claim(tmp_path)
    monkeypatch.setattr(
        issue_queue_module,
        "get_issue",
        lambda repo_slug, number: running_issue(),
        raising=False,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("queued selection and claim mutation must not run")

    monkeypatch.setattr(issue_queue_module, "list_queued_issues", forbidden)
    monkeypatch.setattr(issue_queue_module, "claim_issue", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "issue_queue",
            "--state-root",
            str(tmp_path),
            "--issue",
            "34",
            "--resume-running",
        ],
    )

    assert issue_queue_module.main() == 0
    assert capsys.readouterr().out.strip().endswith("jobs/SV-TEST-001.json")


def test_resume_cli_requires_explicit_issue_before_github_access(
    monkeypatch,
    capsys,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("GitHub must not be accessed without --issue")

    monkeypatch.setattr(issue_queue_module, "list_queued_issues", forbidden)
    monkeypatch.setattr(issue_queue_module, "_gh", forbidden)
    monkeypatch.setattr(sys, "argv", ["issue_queue", "--resume-running"])

    assert issue_queue_module.main() == 2
    assert "--resume-running requires --issue NUMBER" in capsys.readouterr().err
