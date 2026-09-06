import json
from pathlib import Path

import pytest

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
