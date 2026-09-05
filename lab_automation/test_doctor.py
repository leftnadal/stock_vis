from pathlib import Path

from lab_automation.doctor import _check_binary, _git_checks


def test_python_binary_is_visible():
    result = _check_binary("python", ["--version"])
    assert result["ok"]


def test_git_checks_detect_branch(tmp_path: Path):
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "test-branch"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "lab@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Lab Runner"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

    checks = {item["name"]: item for item in _git_checks(tmp_path, "test-branch")}
    assert checks["git_repo"]["ok"]
    assert checks["job_branch_exists"]["ok"]
    assert checks["source_checkout_clean"]["ok"]
