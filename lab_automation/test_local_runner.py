import json
from pathlib import Path
import subprocess

import pytest

from lab_automation.artifact_store import LocalArtifactStore
from lab_automation.contracts import JobEnvelope, Lab
import lab_automation.local_runner as local_runner
from lab_automation.local_runner import (
    _build_codex_prompt,
    _candidate_branch,
    _enforce_write_scope,
    _ensure_minimum_artifacts,
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


def init_job_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "math-lab/test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "lab@example.com"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Lab Runner"],
        cwd=repo,
        check=True,
    )
    authority = repo / "math_lab" / "authority.md"
    authority.parent.mkdir()
    authority.write_text("authority\n", encoding="utf-8")
    subprocess.run(["git", "add", "math_lab/authority.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"],
        cwd=repo,
        check=True,
    )
    return repo


def write_job_file(
    tmp_path: Path,
    *,
    test_commands: list[list[str]] | None = None,
) -> Path:
    path = tmp_path / "job.json"
    path.write_text(
        json.dumps(
            {
                "job_id": "SV-TEST-001",
                "lab": "math_lab",
                "goal": "test runner integrity",
                "branch": "math-lab/test",
                "authority_refs": ["math_lab/authority.md"],
                "expected_outputs": ["report", "tests"],
                "allowed_write_paths": ["math_lab"],
                "db_access": "none",
                "network_policy": "restricted",
                "destructive_actions_allowed": False,
                "status": "queued",
                "test_commands": test_commands or [],
            }
        ),
        encoding="utf-8",
    )
    return path


def fake_executor(
    *,
    report: str | None = "report\n",
    result_json: str | None = '{"status": "complete"}\n',
    data_gaps_json: str | None = "[]\n",
    make_workload_change: bool = True,
    stdout: str = "executor complete\n",
):
    def invoke(worktree, job, raw, prompt, *, dry_run):
        del raw, prompt
        assert not dry_run
        run_root = worktree / ".lab_automation" / "runs" / job.job_id
        result_dir = next(path for path in run_root.iterdir() if path.is_dir())
        for name, content in (
            ("agent_report.md", report),
            ("result.json", result_json),
            ("data_gaps.json", data_gaps_json),
        ):
            if content is not None:
                (result_dir / name).write_text(content, encoding="utf-8")
        if make_workload_change:
            (worktree / "math_lab" / "workload.txt").write_text(
                "meaningful workload\n",
                encoding="utf-8",
            )
        return {
            "command": ["fake-codex"],
            "dry_run": False,
            "stdout": stdout,
            "stderr": "",
            "returncode": 0,
        }

    return invoke


def run_real_job(
    tmp_path: Path,
    monkeypatch,
    executor,
    *,
    test_commands: list[list[str]] | None = None,
) -> tuple[int, Path, list[dict]]:
    repo = init_job_repo(tmp_path)
    job_path = write_job_file(tmp_path, test_commands=test_commands)
    state_root = tmp_path / "state"
    monkeypatch.setattr(local_runner, "_invoke_codex", executor)

    returncode = local_runner.execute_job(
        repo=repo,
        job_path=job_path,
        worktree_root=tmp_path / "worktrees",
        state_root=state_root,
        dry_run=False,
    )
    ledger_path = state_root / "ledger" / "SV-TEST-001.jsonl"
    events = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    return returncode, state_root, events


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


def test_real_run_does_not_synthesize_missing_agent_outputs(tmp_path: Path):
    origins = _ensure_minimum_artifacts(tmp_path, dry_run=False)

    assert origins == {
        "agent_report.md": "missing",
        "result.json": "missing",
        "data_gaps.json": "missing",
    }
    assert list(tmp_path.iterdir()) == []


def test_existing_agent_outputs_keep_agent_generated_origin(tmp_path: Path):
    (tmp_path / "agent_report.md").write_text("report", encoding="utf-8")
    (tmp_path / "result.json").write_text('{"status": "complete"}', encoding="utf-8")
    (tmp_path / "data_gaps.json").write_text("[]", encoding="utf-8")

    origins = _ensure_minimum_artifacts(tmp_path, dry_run=False)

    assert origins["agent_report.md"] == "agent_generated"
    assert origins["result.json"] == "agent_generated"
    assert origins["data_gaps.json"] == "agent_generated"


def test_dry_run_artifacts_are_clearly_marked_placeholders(tmp_path: Path):
    origins = _ensure_minimum_artifacts(tmp_path, dry_run=True)

    assert set(origins.values()) == {"dry_run_placeholder"}
    assert "DRY RUN" in (tmp_path / "agent_report.md").read_text(encoding="utf-8")
    assert '"dry_run_placeholder": true' in (
        tmp_path / "result.json"
    ).read_text(encoding="utf-8")


def test_codex_prompt_treats_local_work_as_already_authorized(tmp_path: Path):
    prompt = _build_codex_prompt(make_job(), tmp_path)

    assert "already authorizes local implementation and validation" in prompt
    assert "Do not pause or ask for another approval" in prompt
    assert "Do not push, merge, deploy" in prompt
    assert "runner-designated output locations" in prompt


def test_pre_commit_hook_accepts_runner_candidate_branch(tmp_path: Path):
    subprocess.run(
        ["git", "init", "-q", "-b", "lab-run/SV-TEST-001/12345678"],
        cwd=tmp_path,
        check=True,
    )
    hook = Path(__file__).parents[1] / "scripts" / "hooks" / "pre-commit"

    result = subprocess.run(
        [str(hook)],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_daily_price_example_requires_probe_and_data_eligibility_tests():
    job_path = (
        Path(__file__).parent
        / "jobs"
        / "math_daily_price_readiness.example.json"
    )
    job = json.loads(job_path.read_text(encoding="utf-8"))

    assert job["test_commands"] == [
        [
            "python",
            "-m",
            "pytest",
            "math_lab/runtime/test_data_eligibility.py",
            "-q",
        ],
        [
            "python",
            "-m",
            "pytest",
            "math_lab/runtime/test_daily_price_readiness.py",
            "-q",
        ],
    ]
    assert any(
        "math_lab/runtime/test_daily_price_readiness.py" in output
        for output in job["expected_outputs"]
    )


def test_approval_question_with_no_outputs_is_not_success(tmp_path: Path, monkeypatch):
    returncode, _, events = run_real_job(
        tmp_path,
        monkeypatch,
        fake_executor(
            report=None,
            result_json=None,
            data_gaps_json=None,
            make_workload_change=False,
            stdout="May I proceed?\n",
        ),
    )

    assert returncode == 1
    output_event = next(row for row in events if row["stage"] == "output_contract")
    assert output_event["status"] == "failed"
    assert set(output_event["metadata"]["missing_artifacts"]) == {
        "agent_report.md",
        "result.json",
        "data_gaps.json",
    }


@pytest.mark.parametrize(
    ("missing_name", "kwargs"),
    [
        ("agent_report.md", {"report": None}),
        ("result.json", {"result_json": None}),
        ("data_gaps.json", {"data_gaps_json": None}),
    ],
)
def test_real_run_rejects_each_missing_artifact(
    tmp_path: Path,
    monkeypatch,
    missing_name: str,
    kwargs: dict[str, str | None],
):
    returncode, _, events = run_real_job(
        tmp_path,
        monkeypatch,
        fake_executor(**kwargs),
    )

    assert returncode == 1
    output_event = next(row for row in events if row["stage"] == "output_contract")
    assert output_event["status"] == "failed"
    assert missing_name in output_event["metadata"]["missing_artifacts"]


@pytest.mark.parametrize(
    ("executor", "error_fragment"),
    [
        (fake_executor(report=" \n"), "agent_report.md must not be empty"),
        (fake_executor(result_json="{}\n"), "empty JSON object"),
        (fake_executor(result_json="not-json\n"), "invalid JSON"),
        (fake_executor(data_gaps_json="not-json\n"), "invalid JSON"),
    ],
)
def test_real_run_rejects_empty_or_invalid_json_artifacts(
    tmp_path: Path,
    monkeypatch,
    executor,
    error_fragment: str,
):
    returncode, _, events = run_real_job(tmp_path, monkeypatch, executor)

    assert returncode == 1
    terminal = next(row for row in events if row["stage"] == "terminal")
    assert error_fragment in terminal["error"]


def test_real_run_requires_meaningful_workload_change(tmp_path: Path, monkeypatch):
    returncode, _, events = run_real_job(
        tmp_path,
        monkeypatch,
        fake_executor(make_workload_change=False),
    )

    assert returncode == 1
    terminal = next(row for row in events if row["stage"] == "terminal")
    assert "meaningful changed path" in terminal["error"]


def test_test_command_side_effect_cannot_count_as_executor_workload_change(
    tmp_path: Path,
    monkeypatch,
):
    returncode, _, events = run_real_job(
        tmp_path,
        monkeypatch,
        fake_executor(make_workload_change=False),
        test_commands=[
            [
                "/bin/sh",
                "-c",
                "printf side-effect > math_lab/test-command-output.txt",
            ]
        ],
    )

    assert returncode == 1
    terminal = next(row for row in events if row["stage"] == "terminal")
    assert "meaningful changed path" in terminal["error"]


def test_commit_failure_preserves_structured_command_diagnostics(
    tmp_path: Path,
    monkeypatch,
):
    repo = init_job_repo(tmp_path)
    job_path = write_job_file(tmp_path)
    state_root = tmp_path / "state"
    real_git = local_runner._git

    def fail_candidate_commit(cwd, *args, check=True):
        if args and args[0] == "commit":
            return subprocess.CompletedProcess(
                ["git", *args],
                9,
                stdout="commit-standard-output\n",
                stderr="commit-standard-error\n",
            )
        return real_git(cwd, *args, check=check)

    monkeypatch.setattr(local_runner, "_invoke_codex", fake_executor())
    monkeypatch.setattr(local_runner, "_git", fail_candidate_commit)

    returncode = local_runner.execute_job(
        repo=repo,
        job_path=job_path,
        worktree_root=tmp_path / "worktrees",
        state_root=state_root,
        dry_run=False,
    )
    ledger_path = state_root / "ledger" / "SV-TEST-001.jsonl"
    events = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    terminal = next(row for row in events if row["stage"] == "terminal")
    failure_ref = terminal["metadata"]["failure_artifact_ref"]
    failure = json.loads(LocalArtifactStore(state_root / "artifacts").read_bytes(failure_ref))

    assert returncode == 1
    assert failure["command"][:2] == ["git", "commit"]
    assert "commit-standard-output" in failure["stdout"]
    assert "commit-standard-error" in failure["stderr"]
    assert failure["returncode"] != 0
    assert failure_ref in terminal["artifact_refs"]


def test_failed_real_run_preserves_worktree_and_records_path(
    tmp_path: Path,
    monkeypatch,
):
    returncode, _, events = run_real_job(
        tmp_path,
        monkeypatch,
        fake_executor(make_workload_change=False),
    )

    terminal = next(row for row in events if row["stage"] == "terminal")
    preserved = Path(terminal["metadata"]["preserved_worktree_path"])
    assert returncode == 1
    assert preserved.is_dir()
