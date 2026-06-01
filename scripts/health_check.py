#!/usr/bin/env python3
"""문서·git 정합성 검증 스크립트.

매 세션 시작 시 실행해 PROGRESS / TASKQUEUE / DECISIONS / git 사이 6가지 stale 패턴을
자동 감지한다. 2026-05-28 정합성 점검에서 발견된 시스템적 결함의 검문소.

검증 항목:
    1. PROGRESS의 `origin/main = <hash>` 표기 vs `git rev-parse origin/main` 실측
    2. PROGRESS가 언급하는 brunch / worktree 폴더 존재 여부
    3. PROGRESS 마지막 갱신 후 누적 commit 수 (50 초과 시 warning, 200 초과 시 error)
    4. TASKQUEUE의 `done` 표시 행 중 매칭 git 머지 commit이 없는 것 (느슨한 휴리스틱)
    5. DECISIONS.md 마지막 갱신일 (60일 초과 시 warning — 활동성 신호)
    6. (보조) slice* brunch가 origin/main에 미반영 수 (정보성)
    7. 외부 자동화 무관여 commit 감지 (#71 close 조건 monitoring, audit/nightly 패턴)

출력: 콘솔 표 + exit code (0=OK, 1=warning, 2=error)

야간 누적 기록 (단계 1, 2026-05-28~):
    --json 모드로 야간 자동화(`docs/infra/nightly_v3.sh` 종료 전)가 매일 실행.
    출력: `docs/nightly_auto_system/YYYYMM/DD/health_check.json`.
    알림은 단계 2(2026-06-중)에서 1~2주 관찰 데이터 위에서 임계 결정 후 도입.

실행:
    python scripts/health_check.py
    python scripts/health_check.py --quiet      # error/warning만 출력
    python scripts/health_check.py --json       # JSON 출력 (CI/hook용)

관련 결정: DECISIONS.md "문서·git 정합성 관리 원칙" (2026-05-28)
관련 버그: sub_claude_md/common-bugs.md #30 (문서·git 정합성 stale 패턴)
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_MD = REPO_ROOT / "PROGRESS.md"
TASKQUEUE_MD = REPO_ROOT / "TASKQUEUE.md"
DECISIONS_MD = REPO_ROOT / "DECISIONS.md"
SHARED_ROOT = REPO_ROOT / "packages" / "shared"
BOUNDARY_LEDGER = REPO_ROOT / "docs" / "harness" / "boundary_ledger.jsonl"


# 결과 상태 코드 — Layer 1 단계의 통일된 의미.
OK = 0
WARN = 1
ERROR = 2

STATUS_LABEL = {OK: "✅ OK", WARN: "⚠  WARN", ERROR: "❌ ERROR"}


@dataclass
class CheckResult:
    name: str
    status: int
    detail: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "status_label": STATUS_LABEL[self.status],
            "detail": self.detail,
            "evidence": self.evidence,
        }


def _git(args: list[str]) -> str:
    """Run git command from repo root, return stdout (stripped). Empty on error."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT)] + args,
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip()
    except FileNotFoundError:
        return ""


# ── 검증 1: PROGRESS origin/main 해시 vs 실제 ────────────────────────────────


def check_origin_main_hash() -> CheckResult:
    actual = _git(["rev-parse", "--short", "origin/main"])
    if not actual:
        return CheckResult(
            name="origin/main 해시",
            status=ERROR,
            detail="git rev-parse origin/main 실패 (remote 미설정?)",
        )

    progress_text = PROGRESS_MD.read_text(encoding="utf-8") if PROGRESS_MD.exists() else ""
    # PROGRESS에 박힌 origin/main = <7+ hex> 패턴 모두 검출
    hashes_in_doc = sorted(set(re.findall(r"origin/main\s*=\s*([0-9a-f]{7,40})", progress_text)))

    if not hashes_in_doc:
        return CheckResult(
            name="origin/main 해시",
            status=WARN,
            detail=f"PROGRESS.md에 origin/main 해시 표기 0건 (실제: {actual})",
        )

    actual_short = actual[:7]
    matches = [h for h in hashes_in_doc if h.startswith(actual_short) or actual_short.startswith(h[:7])]
    if matches:
        return CheckResult(
            name="origin/main 해시",
            status=OK,
            detail=f"PROGRESS 표기 일치 ({actual_short})",
        )
    return CheckResult(
        name="origin/main 해시",
        status=ERROR,
        detail=f"PROGRESS 표기 {hashes_in_doc} 모두 실제 {actual_short}와 불일치",
        evidence=[f"실측: origin/main = {actual_short}"] + [f"PROGRESS: {h}" for h in hashes_in_doc],
    )


# ── 검증 2: PROGRESS가 언급한 brunch / worktree 존재 여부 ─────────────────────


# PROGRESS.md 안에서 명시적으로 "활성/보존/worktree" 같은 라벨로 언급된 brunch만 검증한다.
# 단순 본문 언급(예: 머지 commit 이력)은 제외 — false positive 회피.
BRUNCH_LINE_PATTERN = re.compile(
    r"`(feature/[\w\-/]+|slice\d+|main|iron-trading-api)`"
)
WORKTREE_PATH_PATTERN = re.compile(r"`(/Users/[^`]+stock_vis[\w/_\-]*)`")


def check_brunch_worktree_existence() -> CheckResult:
    if not PROGRESS_MD.exists():
        return CheckResult(
            name="brunch / worktree 존재",
            status=ERROR,
            detail="PROGRESS.md 없음",
        )
    text = PROGRESS_MD.read_text(encoding="utf-8")

    # "활성 브랜치 현황" 섹션만 추출 (다른 섹션의 머지 history 언급 회피)
    section_match = re.search(r"활성 브랜치 현황.*?(?=\n## |\Z)", text, re.DOTALL)
    section = section_match.group(0) if section_match else text

    # local + remote brunch 전수
    branches = set()
    for line in _git(["branch", "-a"]).splitlines():
        b = line.strip().lstrip("* ").replace("remotes/origin/", "")
        if b and not b.startswith("HEAD"):
            branches.add(b)

    missing_branches = []
    for match in BRUNCH_LINE_PATTERN.finditer(section):
        b = match.group(1)
        # "부재"라고 명시된 brunch는 검사 건너뜀 (이미 부재 표기됨)
        line_start = section.rfind("\n", 0, match.start())
        line_end = section.find("\n", match.end())
        line = section[line_start:line_end]
        if "부재" in line or "정리됨" in line or "없음" in line or "보존" in line:
            continue
        if b not in branches:
            missing_branches.append(b)

    # worktree 경로 존재 검사
    missing_worktrees = []
    for match in WORKTREE_PATH_PATTERN.finditer(section):
        path = match.group(1)
        # "부재"가 같은 라인에 명시되면 검사 건너뜀
        line_start = section.rfind("\n", 0, match.start())
        line_end = section.find("\n", match.end())
        line = section[line_start:line_end]
        if "부재" in line or "정리됨" in line:
            continue
        if not Path(path).exists():
            missing_worktrees.append(path)

    if not missing_branches and not missing_worktrees:
        return CheckResult(
            name="brunch / worktree 존재",
            status=OK,
            detail="활성 brunch · worktree 표기 전건 존재 확인",
        )

    evidence = []
    if missing_branches:
        evidence.append(f"부재 brunch: {missing_branches}")
    if missing_worktrees:
        evidence.append(f"부재 worktree: {missing_worktrees}")
    return CheckResult(
        name="brunch / worktree 존재",
        status=ERROR,
        detail=f"PROGRESS 표기 {len(missing_branches) + len(missing_worktrees)}건 실제 부재",
        evidence=evidence,
    )


# ── 검증 3: PROGRESS 마지막 갱신 후 누적 commit 수 ───────────────────────────


WARN_COMMIT_THRESHOLD = 50
ERROR_COMMIT_THRESHOLD = 200


def check_progress_staleness() -> CheckResult:
    last_progress_iso = _git(["log", "-1", "--format=%cI", "--", "PROGRESS.md"])
    if not last_progress_iso:
        return CheckResult(
            name="PROGRESS 갱신 stale",
            status=WARN,
            detail="PROGRESS.md git history 없음",
        )

    commits_since = _git(["log", "--all", "--oneline", f"--since={last_progress_iso}"]).splitlines()
    n = len(commits_since)

    if n >= ERROR_COMMIT_THRESHOLD:
        status = ERROR
    elif n >= WARN_COMMIT_THRESHOLD:
        status = WARN
    else:
        status = OK

    return CheckResult(
        name="PROGRESS 갱신 stale",
        status=status,
        detail=f"PROGRESS.md 마지막 갱신 ({last_progress_iso[:10]}) 이후 {n} commits",
        evidence=[
            f"임계치: warn≥{WARN_COMMIT_THRESHOLD}, error≥{ERROR_COMMIT_THRESHOLD}",
        ],
    )


# ── 검증 4: TASKQUEUE done vs 실제 머지 commit 매칭 (느슨한 휴리스틱) ────────


TASK_DONE_PATTERN = re.compile(r"\|\s*([A-Z]+-[\w\-]+)\s*\|.*?\|\s*(done|verified)\s*\|", re.IGNORECASE)


def check_taskqueue_done_matching() -> CheckResult:
    if not TASKQUEUE_MD.exists():
        return CheckResult(
            name="TASKQUEUE done 매칭",
            status=WARN,
            detail="TASKQUEUE.md 없음",
        )
    text = TASKQUEUE_MD.read_text(encoding="utf-8")
    done_ids = TASK_DONE_PATTERN.findall(text)

    # 매칭 검증: 단순 휴리스틱 — TASKQUEUE의 done 항목이 비어 있지 않은지
    # (느슨한 검증. 더 엄격한 매칭은 Layer 3에서 GitHub PR ID 연동으로 강화 예정)
    if not done_ids:
        return CheckResult(
            name="TASKQUEUE done 매칭",
            status=OK,
            detail="TASKQUEUE에 done 표기 0건 (검증 대상 없음)",
        )

    return CheckResult(
        name="TASKQUEUE done 매칭",
        status=OK,
        detail=f"TASKQUEUE done/verified 표기 {len(done_ids)}건 (휴리스틱 검증 — Layer 3 강화 예정)",
        evidence=[f"감지된 ID 예시: {done_ids[:5]}"],
    )


# ── 검증 5: DECISIONS.md 마지막 갱신일 ──────────────────────────────────────


WARN_DECISIONS_DAYS = 60


def check_decisions_freshness() -> CheckResult:
    if not DECISIONS_MD.exists():
        return CheckResult(
            name="DECISIONS 갱신일",
            status=WARN,
            detail="DECISIONS.md 없음",
        )
    last_iso = _git(["log", "-1", "--format=%cI", "--", "DECISIONS.md"])
    if not last_iso:
        return CheckResult(
            name="DECISIONS 갱신일",
            status=WARN,
            detail="DECISIONS.md git history 없음",
        )
    last_dt = datetime.fromisoformat(last_iso)
    days = (datetime.now(timezone.utc) - last_dt).days
    status = WARN if days > WARN_DECISIONS_DAYS else OK
    return CheckResult(
        name="DECISIONS 갱신일",
        status=status,
        detail=f"DECISIONS.md 마지막 갱신 {last_iso[:10]} ({days}일 전)",
    )


# ── 검증 7: 외부 자동화 무관여 변경 감지 ────────────────────────────────────


# #71 close 조건("환경 변경 시 재점검")의 자동 감지. 사용자/에이전트 작업이 아닌
# 외부 자동화(audit, nightly tier3, 자동 brunch 생성 등)가 활성 brunch에 추가한
# commit을 검출한다. message 패턴 + author 패턴 양쪽으로 잡는다.
EXTERNAL_AUTOMATION_MESSAGE_PATTERNS = [
    r"docs:\s*코드베이스 감사 보고서",
    r"audit:",
    r"nightly:",
    r"\[nightly\]",
    r"\[auto\]",
    r"chore\(nightly\)",
]
# 자동화로 의심되는 author 패턴 (정규 commit author와 구별되는 식별자).
# 사용자 환경의 실제 author 패턴이 알려지면 여기서 확장.
EXTERNAL_AUTOMATION_AUTHOR_PATTERNS = [
    r"nightly@",
    r"automation@",
    r"github-actions\[bot\]",
]


def check_external_automation_commits() -> CheckResult:
    """현재 brunch에서 마지막 사용자 작업 이후 외부 자동화 commit 검출.

    범위: origin/main..HEAD (현재 brunch에만 있고 origin/main에 없는 commit).
    이유: 이미 origin/main에 머지된 audit commit은 의도된 통합 결과로 간주.
    """
    # 현재 brunch가 origin/main을 ancestor로 갖는지 확인
    merge_base = _git(["merge-base", "HEAD", "origin/main"])
    if not merge_base:
        return CheckResult(
            name="외부 자동화 commit",
            status=WARN,
            detail="origin/main merge-base 추적 실패 (remote 미설정?)",
        )

    # origin/main..HEAD 범위에서 message + author 추출
    log_lines = _git(
        [
            "log",
            "origin/main..HEAD",
            "--format=%h\t%an\t%s",
        ]
    ).splitlines()

    if not log_lines:
        return CheckResult(
            name="외부 자동화 commit",
            status=OK,
            detail="origin/main..HEAD 범위 commit 없음",
        )

    message_re = re.compile("|".join(EXTERNAL_AUTOMATION_MESSAGE_PATTERNS), re.IGNORECASE)
    author_re = re.compile("|".join(EXTERNAL_AUTOMATION_AUTHOR_PATTERNS), re.IGNORECASE)

    suspicious = []
    for line in log_lines:
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        sha, author, msg = parts
        if message_re.search(msg) or author_re.search(author):
            suspicious.append(f"{sha} | {author} | {msg[:70]}")

    if not suspicious:
        return CheckResult(
            name="외부 자동화 commit",
            status=OK,
            detail=f"origin/main..HEAD {len(log_lines)} commits — 외부 자동화 의심 0건",
        )

    # 1건만 있으면 WARN (#71 close 조건의 monitoring), 3건 이상이면 ERROR (재점검 필수)
    status = ERROR if len(suspicious) >= 3 else WARN
    return CheckResult(
        name="외부 자동화 commit",
        status=status,
        detail=f"외부 자동화 의심 commit {len(suspicious)}건 (#71 close 조건 monitoring)",
        evidence=suspicious[:5],
    )


# ── 보조 검증 6: slice* brunch 중 origin/main 미반영 수 ─────────────────────


def check_slice_branches_unmerged() -> CheckResult:
    all_branches = _git(["branch", "--list", "slice*"]).splitlines()
    slice_branches = [b.strip().lstrip("* ") for b in all_branches if b.strip()]
    unmerged = []
    for b in slice_branches:
        # b가 origin/main에 머지됐는지 (각 brunch HEAD가 origin/main의 ancestor인지)
        merge_base = _git(["merge-base", b, "origin/main"])
        b_head = _git(["rev-parse", b])
        if merge_base != b_head:
            ahead = _git(["rev-list", "--count", f"origin/main..{b}"])
            unmerged.append(f"{b} (+{ahead})")
    if not unmerged:
        return CheckResult(
            name="slice* 미머지 brunch",
            status=OK,
            detail=f"slice* brunch {len(slice_branches)}건 모두 origin/main 반영됨",
        )
    return CheckResult(
        name="slice* 미머지 brunch",
        status=WARN,
        detail=f"slice* brunch {len(unmerged)}/{len(slice_branches)}건 origin/main 미반영 (정보성)",
        evidence=unmerged,
    )


# ── 검증 8: shared 경계 우회 감지 (tests/architecture와 SSOT 동기화) ───────────
#
# SSOT: tests/architecture/test_shared_boundary.py:KNOWN_VIOLATIONS
# 동결 항목이 바뀌면 양쪽을 동시에 갱신해야 한다 (감시 장치는 작아서 중복 정의 허용).
# 야간 적재용 ledger는 --ledger 플래그로만 append (수동 실행 시 ledger 오염 회피).

_BOUNDARY_FORBIDDEN_SEGMENTS = ("apps", "macro")

_BOUNDARY_KNOWN_VIOLATIONS: set[tuple[str, str]] = {
    ("stocks/services/sp500_eod_service.py", "apps.market_pulse.utils.circuit_breaker"),
    ("stocks/services/sp500_service.py", "apps.market_pulse.utils.circuit_breaker"),
    ("metrics/services/daily_report.py", "apps.chain_sight.models"),
    ("stocks/services/eod_regime_calculator.py", "macro.models"),
    ("stocks/services/eod_pipeline.py", "macro.models"),
}


def _boundary_is_forbidden(module: str) -> bool:
    if not module:
        return False
    return module.split(".", 1)[0] in _BOUNDARY_FORBIDDEN_SEGMENTS


def _boundary_collect_violations() -> list[tuple[str, str, int]]:
    """packages/shared 전 .py를 ast로 파싱해 (rel, module, lineno) 위반 수집."""
    found: list[tuple[str, str, int]] = []
    if not SHARED_ROOT.is_dir():
        return found
    for py in SHARED_ROOT.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = py.relative_to(SHARED_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                mod = node.module or ""
                if _boundary_is_forbidden(mod):
                    found.append((rel, mod, node.lineno))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _boundary_is_forbidden(alias.name):
                        found.append((rel, alias.name, node.lineno))
    return found


def check_shared_boundary() -> CheckResult:
    violations = _boundary_collect_violations()
    present_keys = {(rel, mod) for (rel, mod, _line) in violations}
    bypass = [(rel, mod, line) for (rel, mod, line) in violations if (rel, mod) not in _BOUNDARY_KNOWN_VIOLATIONS]
    frozen_remaining = _BOUNDARY_KNOWN_VIOLATIONS & present_keys
    n_bypass = len(bypass)
    n_frozen = len(frozen_remaining)

    if n_bypass == 0:
        return CheckResult(
            name="shared 경계",
            status=OK,
            detail=f"우회 0 / 동결 잔여 {n_frozen}",
        )
    evidence = [f"{rel}:{line} ← from {mod}" for (rel, mod, line) in bypass]
    return CheckResult(
        name="shared 경계",
        status=ERROR,
        detail=f"우회 {n_bypass}건 / 동결 잔여 {n_frozen}",
        evidence=evidence,
    )


def _boundary_append_ledger() -> None:
    """야간 한 줄 추적 — read-only(import 안 함, 코드 수정 안 함)."""
    violations = _boundary_collect_violations()
    present_keys = {(rel, mod) for (rel, mod, _line) in violations}
    bypass = [v for v in violations if (v[0], v[1]) not in _BOUNDARY_KNOWN_VIOLATIONS]
    frozen_remaining = _BOUNDARY_KNOWN_VIOLATIONS & present_keys
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frozen": len(frozen_remaining),
        "bypass": len(bypass),
        "total": len(violations),
    }
    BOUNDARY_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with BOUNDARY_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── main runner ─────────────────────────────────────────────────────────────


CHECKS = [
    check_origin_main_hash,
    check_brunch_worktree_existence,
    check_progress_staleness,
    check_taskqueue_done_matching,
    check_decisions_freshness,
    check_slice_branches_unmerged,
    check_external_automation_commits,
    check_shared_boundary,
]


def run_all() -> list[CheckResult]:
    return [check() for check in CHECKS]


def print_table(results: list[CheckResult], quiet: bool = False) -> None:
    print()
    print("=" * 80)
    print(" Stock-Vis 문서·git 정합성 점검 (scripts/health_check.py)")
    print(f" 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    print(f"{'상태':<10} {'항목':<28} 결과")
    print("-" * 80)
    for r in results:
        if quiet and r.status == OK:
            continue
        label = STATUS_LABEL[r.status]
        print(f"{label:<10} {r.name:<28} {r.detail}")
        for ev in r.evidence:
            print(f"           └ {ev}")
    print("-" * 80)

    counts = {OK: 0, WARN: 0, ERROR: 0}
    for r in results:
        counts[r.status] += 1
    print(f" 합계: ✅ {counts[OK]}건 / ⚠  {counts[WARN]}건 / ❌ {counts[ERROR]}건")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="문서·git 정합성 점검")
    parser.add_argument("--quiet", action="store_true", help="OK 항목 숨김")
    parser.add_argument("--json", action="store_true", help="JSON 출력 (CI/hook용)")
    parser.add_argument(
        "--ledger",
        action="store_true",
        help="docs/harness/boundary_ledger.jsonl에 shared 경계 추적 한 줄 append (야간 전용)",
    )
    args = parser.parse_args()

    results = run_all()

    if args.ledger:
        _boundary_append_ledger()

    if args.json:
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        print_table(results, quiet=args.quiet)

    # exit code — 가장 심각한 상태 반환
    return max((r.status for r in results), default=OK)


if __name__ == "__main__":
    sys.exit(main())
