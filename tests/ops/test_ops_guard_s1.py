"""OPS-GUARD-S1 — health_check 신규 점검 2건 유닛 테스트.

- H-LAUNCHD-TREE: launchd 잡의 실행 트리가 런타임 worktree/허용 경로인가
- H-ENV-SYMLINK: 런타임 트리 .env가 심링크로 공유 본체를 가리키는가 (D-ENV-SYMLINK-KEEP)

배경: RC-NEO4J-WORKER-TREE — 잡 3건이 11일간 공유 편집 트리에서 돌았는데 자동 점검
부재로 무탐지였다. 이 테스트는 그 재발을 red로 잡는 안전망.
"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from health_check import (  # noqa: E402
    ERROR,
    OK,
    WARN,
    check_env_symlink,
    check_launchd_tree_alignment,
    classify_launchd_path,
    evaluate_env_symlink,
    evaluate_launchd_tree,
    extract_launchd_paths,
)

HOME = "/Users/tester"


def _plist(workdir: str | None = None, args: list[str] | None = None) -> dict:
    d: dict = {}
    if workdir is not None:
        d["WorkingDirectory"] = workdir
    if args is not None:
        d["ProgramArguments"] = args
    return d


# ── extract_launchd_paths ────────────────────────────────────────────────────


def test_extract_takes_workdir_and_script_path():
    p = _plist(
        workdir=f"{HOME}/worktrees/sv-worker-runtime",
        args=["/bin/bash", f"{HOME}/worktrees/sv-worker-runtime/scripts/celery-worker.sh"],
    )
    got = extract_launchd_paths(p)
    assert f"{HOME}/worktrees/sv-worker-runtime" in got
    assert f"{HOME}/worktrees/sv-worker-runtime/scripts/celery-worker.sh" in got
    assert "/bin/bash" in got


def test_extract_skips_path_env_string_with_colons():
    """PATH 값(콜론 포함)은 경로가 아니므로 오탐하지 않는다."""
    p = _plist(args=["/bin/bash", "-c", 'export PATH="$HOME/.nvm/bin:/usr/local/bin:$PATH"; run'])
    got = extract_launchd_paths(p)
    assert not any(":" in tok for tok in got)


def test_extract_handles_home_variable():
    p = _plist(args=["/bin/bash", "-c", "$HOME/worktrees/sv-worker-runtime/x/run.sh >> $HOME/logs/a.log"])
    got = extract_launchd_paths(p)
    assert "$HOME/worktrees/sv-worker-runtime/x/run.sh" in got


def test_extract_requires_token_boundary_for_other_shell_vars():
    """`$NVM_DIR/nvm.sh`의 뒤 조각(`/nvm.sh`)을 경로로 오인하지 않는다.

    회귀: OPS-GUARD-S1 도입 직후 nightly plist에서 오탐 13건이 났다(2026-09-01,
    pg-backup ERROR 해소로 가려져 있던 WARN이 드러나며 발견). $HOME 외의 셸 변수는
    해석할 수 없으므로 그 뒤 경로는 검사 대상이 아니다.
    """
    p = _plist(args=["/bin/bash", "-c", 'source "$NVM_DIR/nvm.sh"; $NIGHTLY_DIR/run_tier1.sh'])
    got = extract_launchd_paths(p)
    assert "/nvm.sh" not in got
    assert "/run_tier1.sh" not in got
    assert "/bin/bash" in got


def test_extract_ignores_slashes_inside_prose_comments():
    """주석 안의 슬래시(`생성/누적`, `TS/dead-code/test`)를 경로로 오인하지 않는다."""
    p = _plist(args=["/bin/bash", "-c", "# tier1(자동 TS/dead-code/test 수정) 브랜치 생성/누적 차단\nrun"])
    got = extract_launchd_paths(p)
    assert not any("dead-code" in t or "누적" in t for t in got)


def test_extract_keeps_paths_after_boundary_chars():
    """공백·따옴표·= 뒤의 절대경로는 정상 추출된다."""
    p = _plist(args=["/bin/bash", "-c", 'OUT="/Users/x/log.txt"; DIR=/Users/x/dir; run /Users/x/a.sh'])
    got = extract_launchd_paths(p)
    assert "/Users/x/log.txt" in got
    assert "/Users/x/dir" in got
    assert "/Users/x/a.sh" in got


def test_extract_ignores_non_string_args():
    p = {"ProgramArguments": ["/bin/bash", 42, None]}
    assert extract_launchd_paths(p) == ["/bin/bash"]


# ── classify_launchd_path ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path,expected",
    [
        (f"{HOME}/worktrees/sv-worker-runtime", "ok"),
        (f"{HOME}/worktrees/sv-api-runtime/scripts/daphne-web.sh", "ok"),
        (f"{HOME}/worktrees/sv-web-runtime/frontend", "ok"),
        (f"{HOME}/neo4j/bin/neo4j", "ok"),
        (f"{HOME}/stock-vis-nightly/logs/a.log", "ok"),
        (f"{HOME}/.nvm/versions/node/v22.19.0/bin/npm", "ok"),
        ("/bin/bash", "ok"),
        ("/usr/local/bin/tool", "ok"),
        ("$HOME/worktrees/sv-worker-runtime/x.sh", "ok"),
        (f"{HOME}/Desktop/stock_vis", "shared_tree"),
        (f"{HOME}/Desktop/stock_vis/scripts/pg-backup.sh", "shared_tree"),
        ("$HOME/Desktop/stock_vis/scripts/x.sh", "shared_tree"),
        (f"{HOME}/some/other/place", "unknown"),
        ("/opt/homebrew/bin/x", "ok"),
    ],
)
def test_classify_launchd_path(path, expected):
    assert classify_launchd_path(path, HOME) == expected


def test_classify_rejects_prefix_lookalike():
    """sv-worker-runtime-old 같은 유사 이름은 허용되지 않는다."""
    assert classify_launchd_path(f"{HOME}/worktrees/sv-worker-runtime-old", HOME) == "unknown"


# ── evaluate_launchd_tree (3분기) ────────────────────────────────────────────


def test_evaluate_ok_when_all_runtime_trees():
    plists = {
        "celery-worker": _plist(
            workdir=f"{HOME}/worktrees/sv-worker-runtime",
            args=["/bin/bash", f"{HOME}/worktrees/sv-worker-runtime/scripts/celery-worker.sh"],
        ),
        "neo4j": _plist(workdir=f"{HOME}/neo4j", args=[f"{HOME}/neo4j/bin/neo4j", "console"]),
    }
    r = evaluate_launchd_tree(plists, HOME)
    assert r.status == OK
    assert "2건" in r.detail


def test_evaluate_error_on_shared_tree():
    """이번 사고의 재현 — 공유 편집 트리를 가리키면 ERROR."""
    plists = {
        "celery-worker": _plist(workdir=f"{HOME}/worktrees/sv-worker-runtime"),
        "pg-backup": _plist(
            workdir=f"{HOME}/Desktop/stock_vis",
            args=["/bin/bash", f"{HOME}/Desktop/stock_vis/scripts/pg-backup.sh"],
        ),
    }
    r = evaluate_launchd_tree(plists, HOME)
    assert r.status == ERROR
    assert any("pg-backup" in e for e in r.evidence)


def test_evaluate_warn_on_unknown_path():
    plists = {"weird": _plist(workdir=f"{HOME}/elsewhere/tree")}
    r = evaluate_launchd_tree(plists, HOME)
    assert r.status == WARN
    assert any("weird" in e for e in r.evidence)


def test_evaluate_shared_tree_wins_over_unknown():
    """ERROR가 WARN보다 우선 — 둘 다 있으면 ERROR."""
    plists = {
        "bad": _plist(workdir=f"{HOME}/Desktop/stock_vis"),
        "weird": _plist(workdir=f"{HOME}/elsewhere"),
    }
    assert evaluate_launchd_tree(plists, HOME).status == ERROR


# ── check_launchd_tree_alignment (파일시스템 경유) ───────────────────────────


def _write_plist(d: Path, label: str, content: dict) -> None:
    with (d / f"com.stockvis.{label}.plist").open("wb") as fh:
        plistlib.dump(content, fh)


def test_check_launchd_reads_real_plist_files(tmp_path):
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    _write_plist(agents, "good", _plist(workdir=f"{HOME}/worktrees/sv-worker-runtime"))
    _write_plist(agents, "bad", _plist(workdir=f"{HOME}/Desktop/stock_vis"))
    r = check_launchd_tree_alignment(agents_dir=agents, home=HOME)
    assert r.status == ERROR
    assert any("bad" in e for e in r.evidence)


def test_check_launchd_skips_when_dir_absent(tmp_path):
    """비-macOS/비-런타임 환경 안전."""
    r = check_launchd_tree_alignment(agents_dir=tmp_path / "nope", home=HOME)
    assert r.status == OK
    assert "skip" in r.detail


def test_check_launchd_skips_when_no_stockvis_jobs(tmp_path):
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    (agents / "com.other.app.plist").write_bytes(b"")
    r = check_launchd_tree_alignment(agents_dir=agents, home=HOME)
    assert r.status == OK


def test_check_launchd_warns_when_all_unreadable(tmp_path):
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    (agents / "com.stockvis.broken.plist").write_text("not a plist at all")
    r = check_launchd_tree_alignment(agents_dir=agents, home=HOME)
    assert r.status == WARN
    assert "판독 불가" in r.detail


def test_check_launchd_tolerates_partial_unreadable(tmp_path):
    """일부만 손상이면 나머지로 판정하되 증거에 남긴다."""
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    _write_plist(agents, "bad", _plist(workdir=f"{HOME}/Desktop/stock_vis"))
    (agents / "com.stockvis.broken.plist").write_text("garbage")
    r = check_launchd_tree_alignment(agents_dir=agents, home=HOME)
    assert r.status == ERROR
    assert any("판독 불가" in e for e in r.evidence)


# ── evaluate_env_symlink (3분기) ─────────────────────────────────────────────


def test_env_ok_when_symlink_resolves():
    r = evaluate_env_symlink([("sv-worker-runtime", True, True, True)])
    assert r.status == OK


def test_env_error_when_symlink_broken():
    r = evaluate_env_symlink([("sv-worker-runtime", True, True, False)])
    assert r.status == ERROR
    assert any("소실" in e for e in r.evidence)


def test_env_error_when_missing():
    r = evaluate_env_symlink([("sv-api-runtime", False, False, False)])
    assert r.status == ERROR
    assert any("부재" in e for e in r.evidence)


def test_env_warn_when_plain_file():
    """심링크 유지가 결정(D-ENV-SYMLINK-KEEP) — 일반 파일은 drift 가능 WARN."""
    r = evaluate_env_symlink([("sv-worker-runtime", True, False, True)])
    assert r.status == WARN
    assert "drift" in r.detail


def test_env_broken_wins_over_plain():
    r = evaluate_env_symlink(
        [("sv-worker-runtime", True, True, False), ("sv-api-runtime", True, False, True)]
    )
    assert r.status == ERROR


# ── check_env_symlink (파일시스템 경유) ──────────────────────────────────────


def test_check_env_symlink_ok(tmp_path):
    wt = tmp_path / "worktrees"
    (wt / "sv-worker-runtime").mkdir(parents=True)
    real = tmp_path / "shared.env"
    real.write_text("SECRET=should-never-be-read\n")
    (wt / "sv-worker-runtime" / ".env").symlink_to(real)
    r = check_env_symlink(worktrees_dir=wt)
    assert r.status == OK
    joined = r.detail + " ".join(r.evidence)
    assert "should-never-be-read" not in joined  # 값 미출력 계약


def test_check_env_symlink_detects_broken(tmp_path):
    wt = tmp_path / "worktrees"
    (wt / "sv-api-runtime").mkdir(parents=True)
    (wt / "sv-api-runtime" / ".env").symlink_to(tmp_path / "gone.env")
    r = check_env_symlink(worktrees_dir=wt)
    assert r.status == ERROR


def test_check_env_symlink_skips_without_worktrees(tmp_path):
    r = check_env_symlink(worktrees_dir=tmp_path / "nope")
    assert r.status == OK
    assert "skip" in r.detail


def test_check_env_symlink_skips_when_no_runtime_trees(tmp_path):
    wt = tmp_path / "worktrees"
    (wt / "sv-something-else").mkdir(parents=True)
    r = check_env_symlink(worktrees_dir=wt)
    assert r.status == OK
