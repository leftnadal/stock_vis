"""NT-11 stray celery 가드 회귀 테스트 (detection-only, psutil 모킹).

검증 대상: `packages.shared.metrics.services.daily_report._detect_stray_celery`
- 루트 밖 cwd(`.Trash` 등) celery 프로세스 → offender로 잡힘
- 루트 안 cwd → 잡히지 않음
- celery 아닌 프로세스 → 무시
- offender 0건 → 빈 리스트 (무음: suggestion·메일줄 미발생 전제)

원본 사건: 좀비 Beat 56670 (cwd=`~/.Trash/stock_vis.icloud_backup.20260516_144329`,
5/21~6/6 16일 invisible). 본 가드는 매일 07:00 KST daily_report 발사 시 가시화.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from packages.shared.metrics.services import daily_report


def _make_proc(pid: int, cmdline: list[str], cwd: str | None):
    """psutil.Process 모의 객체. info dict에서 가져가는 패턴 미러링."""
    proc = MagicMock()
    proc.info = {"pid": pid, "cmdline": cmdline, "cwd": cwd}
    return proc


@patch.object(daily_report, "_allowed_roots")
def test_stray_celery_offender_picked_when_cwd_outside_roots(
    mock_allowed_roots,
):
    """루트 밖 cwd 가진 celery 프로세스는 offender로 잡힘."""
    mock_allowed_roots.return_value = ["/Users/dev/Desktop/stock_vis"]

    procs = [
        _make_proc(
            pid=56670,
            cmdline=["python", "celery", "-A", "config", "beat", "-l", "info"],
            cwd="/Users/dev/.Trash/stock_vis.icloud_backup.20260516_144329",
        ),
    ]

    with patch("psutil.process_iter", return_value=iter(procs)):
        offenders = daily_report._detect_stray_celery()

    assert len(offenders) == 1
    assert offenders[0]["pid"] == 56670
    assert ".Trash" in offenders[0]["cwd"]


@patch.object(daily_report, "_allowed_roots")
def test_stray_celery_not_picked_when_cwd_inside_root(mock_allowed_roots):
    """정규 worktree 루트 안 cwd는 잡히지 않음."""
    mock_allowed_roots.return_value = ["/Users/dev/Desktop/stock_vis"]

    procs = [
        _make_proc(
            pid=15151,
            cmdline=["python", "celery", "-A", "config", "beat", "-l", "info"],
            cwd="/Users/dev/Desktop/stock_vis",
        ),
        _make_proc(
            pid=17499,
            cmdline=[
                "python",
                "celery",
                "-A",
                "config",
                "worker",
                "--concurrency=4",
            ],
            cwd="/Users/dev/Desktop/stock_vis/some_subdir",
        ),
    ]

    with patch("psutil.process_iter", return_value=iter(procs)):
        offenders = daily_report._detect_stray_celery()

    assert offenders == []


@patch.object(daily_report, "_allowed_roots")
def test_stray_celery_ignores_non_celery_process(mock_allowed_roots):
    """celery 아닌 프로세스(cwd가 루트 밖이어도)는 무시."""
    mock_allowed_roots.return_value = ["/Users/dev/Desktop/stock_vis"]

    procs = [
        _make_proc(
            pid=99999,
            cmdline=["python", "manage.py", "shell"],
            cwd="/Users/dev/.Trash/old_tree",
        ),
        _make_proc(pid=88888, cmdline=["node", "next", "dev"], cwd="/tmp"),
    ]

    with patch("psutil.process_iter", return_value=iter(procs)):
        offenders = daily_report._detect_stray_celery()

    assert offenders == []


@patch.object(daily_report, "_allowed_roots")
def test_stray_celery_empty_when_no_offender(mock_allowed_roots):
    """offender 0건 → 빈 리스트 (무음 — suggestion·메일줄 미발생 전제)."""
    mock_allowed_roots.return_value = ["/Users/dev/Desktop/stock_vis"]

    procs = [
        _make_proc(
            pid=15151,
            cmdline=["python", "celery", "-A", "config", "beat"],
            cwd="/Users/dev/Desktop/stock_vis",
        ),
    ]

    with patch("psutil.process_iter", return_value=iter(procs)):
        offenders = daily_report._detect_stray_celery()

    assert offenders == []


@patch.object(daily_report, "_allowed_roots")
def test_stray_celery_handles_none_cwd(mock_allowed_roots):
    """cwd가 None인 프로세스(권한 부재 등)는 skip — 예외 안 던짐."""
    mock_allowed_roots.return_value = ["/Users/dev/Desktop/stock_vis"]

    procs = [
        _make_proc(
            pid=11111,
            cmdline=["python", "celery", "-A", "config", "beat"],
            cwd=None,
        ),
    ]

    with patch("psutil.process_iter", return_value=iter(procs)):
        offenders = daily_report._detect_stray_celery()

    assert offenders == []


@patch.object(daily_report, "_allowed_roots")
def test_stray_celery_empty_when_no_allowed_roots(mock_allowed_roots):
    """`git worktree list` 실패(빈 루트)면 안전하게 빈 리스트 반환."""
    mock_allowed_roots.return_value = []

    procs = [
        _make_proc(
            pid=56670,
            cmdline=["python", "celery", "-A", "config", "beat"],
            cwd="/Users/dev/.Trash/old_tree",
        ),
    ]

    with patch("psutil.process_iter", return_value=iter(procs)):
        offenders = daily_report._detect_stray_celery()

    assert offenders == []


def test_allowed_roots_parses_git_worktree_list():
    """`git worktree list --porcelain` 출력에서 worktree 경로만 추출."""
    fake_output = (
        "worktree /Users/dev/Desktop/stock_vis\n"
        "HEAD abc123\n"
        "branch refs/heads/main\n"
        "\n"
        "worktree /Users/dev/Desktop/stock_vis_nt11\n"
        "HEAD def456\n"
        "branch refs/heads/monorepo/sess-mgmt-nt11-stray-guard\n"
    )
    mock_result = MagicMock()
    mock_result.stdout = fake_output

    with patch("subprocess.run", return_value=mock_result):
        roots = daily_report._allowed_roots()

    assert "/Users/dev/Desktop/stock_vis" in roots
    assert "/Users/dev/Desktop/stock_vis_nt11" in roots
    assert len(roots) == 2
