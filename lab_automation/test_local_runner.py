from pathlib import Path

import pytest

from lab_automation.contracts import JobEnvelope, Lab
from lab_automation.local_runner import (
    _candidate_branch,
    _enforce_write_scope,
    _path_allowed,
    _validate_job,
)


def make_job(**overrides):
    values = dict(
        job_id="SV-TEST-001",
        lab=Lab.MATH,
        goal="test",
        branch="math-lab/test",
        authority_refs=("math_lab/README.md",),
        expected_outputs=("report",),
        allowed_write_paths=("math_lab",),
        db_access="read_only",
        network_policy="restricted",
        destructive_actions_allowed=False,
    )
    values.update(overrides)
    return JobEnvelope(**values)


def test_rejects_main_branch():
    with pytest.raises(ValueError):
        _validate_job(make_job(branch="main"))


def test_rejects_write_db_access():
    with pytest.raises(ValueError):
        _validate_job(make_job(db_access="read_write"))


def test_rejects_destructive_mode():
    with pytest.raises(ValueError):
        _validate_job(make_job(destructive_actions_allowed=True))


def test_write_scope_accepts_descendant():
    assert _path_allowed("math_lab/results/report.md", ("math_lab",))


def test_write_scope_rejects_other_lab():
    with pytest.raises(PermissionError):
        _enforce_write_scope(["research_lab/file.md"], ("math_lab",))


def test_candidate_branch_is_local_run_specific():
    branch = _candidate_branch("SV:MATH:1", "12345678-abcd")
    assert branch == "lab-run/SV-MATH-1/12345678"
