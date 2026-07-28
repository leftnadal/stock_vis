#!/usr/bin/env python3
"""문서·git 정합성 검증 스크립트.

매 세션 시작 시 실행해 PROGRESS / TASKQUEUE / DECISIONS / git 사이 6가지 stale 패턴을
자동 감지한다. 2026-05-28 정합성 점검에서 발견된 시스템적 결함의 검문소.

검증 항목:
    1. PROGRESS.md 마지막 커밋 시각이 임계(72h) 넘게 묵었는지 (시간기반, B2 2026-07-02; 구 origin/main 해시대조 폐기)
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

# 환경 의존 known-fail 레지스트리 (회귀 게이트 제외 대상 SSOT).
# 이관·코드 회귀 신호를 환경 fail이 가리지 않게 명시 제외. {test_id: 사유}.
KNOWN_TEST_FAILS: dict[str, str] = {
    "tests/unit/news/test_api.py::TestNewsViewSet::test_stock_news_refresh_true": (
        "Finnhub API 키가 테스트 환경에 없음 — 환경 의존, 이관/코드와 무관. "
        "BOUNDARY-LLM 슬라이스 ④ Part ①-sync 회귀에서 선존 확인(2026-06-26)."
    ),
    # 아래 3건(test_news_entity_deduplication)은 지시서⑫ C2 에서 provider 주입(S5 seam)으로
    # env-독립 상환 완료 → env -i 격리서 green → 레지스트리에서 제거(스테일 방지).
    # 제거 근거: NewsAggregatorService(finnhub=FinnhubNewsProvider(api_key='test...')) 주입.
}


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


# ── 검증 1: PROGRESS.md 갱신 신선도 (시간기반, B2 재설계 2026-07-02) ────────────
#
# 구설계(폐기): PROGRESS에 박은 `origin/main = <hash>`를 origin/main recent-N과 대조.
#   함정 3종 → DECISIONS D-OPS-HCHECK-B2:
#     (1) 규약상 PROGRESS는 캐시(진실 아님)인데 그 lag을 blocking ERROR로 취급 = category error.
#     (2) 갱신 커밋이 자기 push-후 hash를 본문에 못 적는 self-referential → 수렴 불가.
#     (3) fast-main(인간 병렬 세션 ~20min 간격 land) + 동시쓰기 → 구조적 오발(마커 treadmill).
# 신설(B2): PROGRESS.md의 마지막 커밋 시각(committer epoch, UTC)이 임계 M시간 넘게
#   묵었는지만 본다. blocking(진짜 방치 차단) 유지, 해시 의존 제거 → self-ref·동시쓰기 무관.
#   committer-ts 사용(파일 mtime 금지 — 클론/체크아웃마다 불안정).
#
# M(임계)=72h. 근거(STEP 0 실측 2026-07-02): PROGRESS 커밋 최대 정상 gap ≈ 22.6h(활성 야간
#   사이클); 주말(금저녁→월아침) ~60-72h 정상 가능 → 48h는 주말 오발 위험 → 72h로 마진.
PROGRESS_STALE_THRESHOLD_H = 72.0


def is_progress_stale(progress_ts: int, now_ts: int, threshold_h: float) -> bool:
    """PROGRESS.md 마지막 갱신이 threshold_h 시간 넘게 묵었는가 (순수함수, 테스트 주입용)."""
    return (now_ts - progress_ts) / 3600.0 > threshold_h


def check_origin_main_hash() -> CheckResult:
    """PROGRESS.md 갱신 신선도 (시간기반, B2). 함수명·display name·등록은 레지스트리/JSON 호환 위해 유지."""
    ts_raw = _git(["log", "-1", "--format=%ct", "--", "PROGRESS.md"])
    if not ts_raw:
        return CheckResult(
            name="origin/main 해시",
            status=ERROR,
            detail="PROGRESS.md 커밋 이력 조회 실패 (git log 빈 결과)",
        )
    progress_ts = int(ts_raw)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    age_h = (now_ts - progress_ts) / 3600.0
    if is_progress_stale(progress_ts, now_ts, PROGRESS_STALE_THRESHOLD_H):
        return CheckResult(
            name="origin/main 해시",
            status=ERROR,
            detail=f"PROGRESS.md {age_h:.1f}h 미갱신 (임계 {PROGRESS_STALE_THRESHOLD_H:.0f}h) — 방치 의심",
        )
    return CheckResult(
        name="origin/main 해시",
        status=OK,
        detail=f"PROGRESS.md {age_h:.1f}h 전 갱신 (시간기반, 임계 {PROGRESS_STALE_THRESHOLD_H:.0f}h 이내)",
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


# ── 검증 4b: TASKQUEUE 주장 상태 vs 증거 대조 (advisory, WARN-only) ──────────
# 목적: 스테일 하네스 항목 조기 감지. 트랙이 실제로 landed(산출물 존재 + DECISIONS 종결)
# 인데 TASKQUEUE가 그 사실을 acknowledge하지 않으면(여전히 미착수/DORMANT처럼 보이면) WARN.
# 근거 사례 = BOUNDARY-LLM DORMANT-vs-landed 스테일(지시서⑪ 발견, ⑫ C3 가드화).
# ★ 판정 불변: 항상 OK/WARN 만 반환(ERROR 없음) = pass/fail baseline 무변경(advisory).
# 오탐 방지: "이력 보존용 옛 문구"가 남아 있어도, landed **ack 토큰**의 존재만 확인하므로
# retained 히스토리에 false-positive 하지 않는다(정합=ack 토큰 有).

# 규칙 = landed 판정에 필요한 증거(DECISIONS 종결 문구 + 산출물 경로) + TASKQUEUE ack 토큰.
_CLAIM_EVIDENCE_RULES: list[dict] = [
    {
        "label": "BOUNDARY-LLM",
        "decisions_landed": "BOUNDARY-LLM 실행 완료",
        "artifact": "packages/shared/llm/core.py",
        "ack_tokens": ["종결·LANDED", "실행 완료 (landed)", "상태 정정 (2026-07-13"],
    },
]


def _evaluate_claim_evidence(tq_text, dec_text, artifact_exists, rules) -> list[str]:
    """순수 함수(테스트 가능). landed 증거가 있는데 TASKQUEUE ack 없는 규칙의 경고 목록 반환."""
    mismatches: list[str] = []
    for rule in rules:
        landed = (rule["decisions_landed"] in dec_text) and artifact_exists(rule["artifact"])
        if not landed:
            continue  # landed 증거 없음 → 검증 대상 아님
        acknowledged = any(tok in tq_text for tok in rule["ack_tokens"])
        if not acknowledged:
            mismatches.append(
                f"{rule['label']}: landed 증거(DECISIONS 종결 + {rule['artifact']}) 있으나 "
                f"TASKQUEUE에 landed ack 토큰 부재 — 정합 필요(스테일 주장 의심)"
            )
    return mismatches


def check_taskqueue_claim_vs_evidence() -> CheckResult:
    tq = TASKQUEUE_MD.read_text(encoding="utf-8") if TASKQUEUE_MD.exists() else ""
    dec = DECISIONS_MD.read_text(encoding="utf-8") if DECISIONS_MD.exists() else ""
    mism = _evaluate_claim_evidence(
        tq, dec, lambda a: (REPO_ROOT / a).exists(), _CLAIM_EVIDENCE_RULES
    )
    if mism:
        return CheckResult(
            name="TASKQUEUE 주장 vs 증거",
            status=WARN,
            detail=f"스테일 주장 의심 {len(mism)}건 (landed인데 TASKQUEUE 미ack)",
            evidence=mism,
        )
    return CheckResult(
        name="TASKQUEUE 주장 vs 증거",
        status=OK,
        detail=f"주장-증거 정합 (규칙 {len(_CLAIM_EVIDENCE_RULES)}건 대조, 불일치 0)",
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

# #1·#2: 2026-06-01 BOUNDARY-1 청소 완료 (circuit_breaker → shared)
# #3: 2026-06-01 BOUNDARY-2 청소 완료 (daily_report → apps.get_model 동적 lookup)
# #4·#5: 2026-06-04 BOUNDARY-3 청소 완료 (eod_* → VIXProvider 의존 역전 + 등록 패턴)
_BOUNDARY_KNOWN_VIOLATIONS: set[tuple[str, str]] = set()


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


# ── 검증 9: 외부-LLM-직접호출 감지 (BOUNDARY-LLM 슬라이스 ③) ──────────────────
#
# SSOT: tests/architecture/test_llm_direct_call_boundary.py:KNOWN_VIOLATIONS
# 동결 항목이 바뀌면 양쪽(테스트 + 여기)을 동시에 갱신해야 한다 (규약: 한쪽만 고치면 드리프트).
# 동결 N = 슬라이스 ④ burn-down 게이지(이관 1곳 = 동결 1곳 해제, 0 = 완료).
# 코어 provider(packages/shared/llm/**)는 정상 직접호출 — 예외.

_LLM_SCAN_DIRS = ("apps", "packages", "services")
_LLM_CORE_EXEMPT_PREFIX = "packages/shared/llm/"
_LLM_NAME_CALLS = frozenset({"Anthropic", "AsyncAnthropic"})

# tests/architecture/test_llm_direct_call_boundary.py:KNOWN_VIOLATIONS 와 일치(슬라이스 ④ burn-down).
# korean_overview는 슬라이스 ②에서 이관 완료 → 목록에 없음(회귀 잠금).
# 슬라이스 ④ #3 완료 → 빈 목록 = BOUNDARY-LLM burn-down 종결(23→0, 전 소비처 코어 단일 경유).
_LLM_KNOWN_VIOLATIONS: set[tuple[str, str]] = set()


def _llm_call_identifier(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name) and func.id in _LLM_NAME_CALLS:
        return func.id
    if isinstance(func, ast.Attribute):
        if func.attr == "Client" and isinstance(func.value, ast.Name) and func.value.id == "genai":
            return "genai.Client"
        if func.attr == "GenerativeModel":
            return "GenerativeModel"
    return None


def _llm_collect_violations() -> list[tuple[str, str, int]]:
    """apps/packages/services 전 .py를 ast로 파싱해 (rel, identifier, lineno) 직접호출 수집.

    코어 provider(_LLM_CORE_EXEMPT_PREFIX)는 제외.
    """
    found: list[tuple[str, str, int]] = []
    for d in _LLM_SCAN_DIRS:
        root = REPO_ROOT / d
        if not root.is_dir():
            continue
        for py in root.rglob("*.py"):
            rel = py.relative_to(REPO_ROOT).as_posix()
            if rel.startswith(_LLM_CORE_EXEMPT_PREFIX):
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    ident = _llm_call_identifier(node)
                    if ident is not None:
                        found.append((rel, ident, node.lineno))
    return found


def check_llm_direct_call_boundary() -> CheckResult:
    violations = _llm_collect_violations()
    present_keys = {(rel, ident) for (rel, ident, _line) in violations}
    bypass = [(rel, ident, line) for (rel, ident, line) in violations if (rel, ident) not in _LLM_KNOWN_VIOLATIONS]
    frozen_remaining = _LLM_KNOWN_VIOLATIONS & present_keys
    n_bypass = len(bypass)
    n_frozen = len(frozen_remaining)

    if n_bypass == 0:
        return CheckResult(
            name="외부-LLM 경계",
            status=OK,
            detail=f"신규 직접호출 0 / 동결 잔여 {n_frozen} (슬라이스 ④ 게이지)",
        )
    evidence = [f"{rel}:{line} ← {ident}(...)" for (rel, ident, line) in bypass]
    return CheckResult(
        name="외부-LLM 경계",
        status=ERROR,
        detail=f"신규 직접호출 {n_bypass}건 / 동결 잔여 {n_frozen}",
        evidence=evidence,
    )


# ── 검증 10: 환경 known-fail 레지스트리 (회귀 게이트 제외 명시) ────────────────


def check_known_test_fails() -> CheckResult:
    """KNOWN_TEST_FAILS를 명시 노출 — 회귀 게이트가 이 환경 fail을 제외함을 표기.

    pytest를 직접 돌리지 않는다(문서성 SSOT). 회귀 카운트 시 이 목록을 빼면
    이관/코드 회귀 신호가 환경 fail에 묻히지 않는다.
    """
    n = len(KNOWN_TEST_FAILS)
    evidence = [f"{tid}  ← {reason}" for tid, reason in KNOWN_TEST_FAILS.items()]
    return CheckResult(
        name="known-fail 레지스트리",
        status=OK,
        detail=f"환경 known-fail {n}건 (회귀 게이트 제외, 이관 무관)",
        evidence=evidence,
    )


# ── 검증 8: 발행 로그(IssuanceLog) 신선도 (D-HC-ISSUANCE) ─────────────────────
#
# bake 자가검증(런타임)의 짝 = 검문소(정합성). 최근 거래일 발행 로그가 존재하고
# 최근성을 유지하는지 최소 검사 — #46(migration 미적용 → write 조용히 실패,
# silent 로깅 손실) 재발 탐지. DB 접근이 이 스크립트 유일하므로 Django lazy setup +
# 전 구간 방어(비-런타임 환경·빈 이력은 OK-skip = zero-noise 원칙 준수).

# 최근 거래일 임계(달력일) — 주말(2) + 연휴 여유. 초과 시 stale 의심(WARN).
ISSUANCE_STALE_DAYS = 5


def check_issuance_log_freshness() -> CheckResult:
    """최근 거래일 IssuanceLog 행 존재 + 최근성(published_at) 최소 검사. [D-HC-ISSUANCE]

    - 비-런타임 환경(Django/DB 미가용)·빈 이력 → OK-skip(노이즈 0).
    - 테이블 부재/조회 실패(#46 핵심 증상) → WARN.
    - 이력은 있으나 최근 거래일이 ISSUANCE_STALE_DAYS 초과 → WARN(stale 의심).
    - 주말·휴장 허용 오차 = ISSUANCE_STALE_DAYS(달력일)로 흡수.
    """
    name = "발행 로그 신선도"
    try:
        import os

        import django

        # 스크립트 직접 실행 시 sys.path[0]=scripts/ 라 config/packages 미발견 → REPO_ROOT 보강.
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
        from packages.shared.stocks.models import IssuanceLog
    except Exception as e:  # noqa: BLE001 — 비-런타임 환경은 검사 대상 아님
        return CheckResult(
            name=name,
            status=OK,
            detail="Django/DB 미가용 — 검사 생략(비-런타임 환경)",
            evidence=[str(e)[:120]],
        )

    try:
        latest = IssuanceLog.objects.order_by("-signal_date").first()
    except Exception as e:  # noqa: BLE001 — 테이블 부재(#46) 등
        return CheckResult(
            name=name,
            status=WARN,
            detail="IssuanceLog 조회 실패 — 테이블 부재 가능(#46 증상)",
            evidence=[str(e)[:120]],
        )

    if latest is None:
        return CheckResult(
            name=name,
            status=OK,
            detail="발행 로그 이력 없음 — 검사 생략(bake 미실행 환경)",
        )

    latest_date = latest.signal_date
    count = IssuanceLog.objects.filter(signal_date=latest_date).count()
    age_days = (datetime.now().date() - latest_date).days
    published = getattr(latest, "published_at", None)
    pub_str = published.date().isoformat() if published else "N/A"

    if age_days > ISSUANCE_STALE_DAYS:
        return CheckResult(
            name=name,
            status=WARN,
            detail=f"최근 발행 로그 {age_days}일 전({latest_date}) — stale 의심(임계 {ISSUANCE_STALE_DAYS}일)",
            evidence=[f"최근 거래일 행수={count}, published_at={pub_str}"],
        )
    return CheckResult(
        name=name,
        status=OK,
        detail=f"최근 거래일 {latest_date} 행 {count}건 (age {age_days}일 ≤ {ISSUANCE_STALE_DAYS})",
        evidence=[f"published_at={pub_str}"],
    )


# ── 검증 9: 실행 트리 정합 (D-SYNC-ENTRYPOINT) ───────────────────────────────
#
# 이 스크립트가 실행되는 트리가 origin/main 대비 뒤처지면 = 구버전 health_check일
# 수 있음(신규 항목 누락). #47 재귀(worker_sync에 이어 health_check도 stale 가능)를
# 결과 자체에 표기 — "이 리포트가 최신 코드로 돈 게 맞나"를 리포트가 스스로 경고.
# fetch 불가(오프라인) → OK-skip. 순수 분류는 classify_tree_alignment로 분리(테스트).


def classify_tree_alignment(fetch_ok: bool, head: str, origin: str) -> int:
    """실행 트리 정합 상태 → status. fetch 실패는 skip(OK), 뒤처짐은 WARN."""
    if not fetch_ok:
        return OK
    if head and origin and head == origin:
        return OK
    return WARN


def check_execution_tree_alignment() -> CheckResult:
    name = "실행 트리 정합"
    fetch_ok = (
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "fetch", "origin", "--quiet"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    head = _git(["rev-parse", "HEAD"])
    origin = _git(["rev-parse", "origin/main"])
    status = classify_tree_alignment(fetch_ok, head, origin)
    if not fetch_ok:
        return CheckResult(
            name=name, status=OK, detail="fetch 불가(오프라인) — 정합 검사 생략"
        )
    short = lambda h: h[:7] if h else "?"  # noqa: E731
    if status == WARN:
        return CheckResult(
            name=name,
            status=WARN,
            detail=f"실행 트리가 origin/main 뒤처짐 — 구버전 항목 누락 가능(#47)",
            evidence=[
                f"HEAD={short(head)} ≠ origin/main={short(origin)}",
                f"트리: {REPO_ROOT}",
                "→ 'sv health'(런타임 트리 최신화 후 실행) 권장",
            ],
        )
    return CheckResult(
        name=name,
        status=OK,
        detail=f"실행 트리 = origin/main ({short(head)}) 정합",
    )


# ── 검증 13: monitor refresh 태스크 신선도 (MON-P2-BEAT §6) ──────────────────
#
# ※ CHECKS 레지스트리 기준 13번째 항목. 지시서 §6의 "12번째"는 stale count(issuance·
#   execution_tree 추가 전 11 가정) 기준 — 착수 시점 실제 12개 → 이 항목이 13번째.
# refresh_monitors_task(18:45 ET beat)는 성공 시 각 stock Monitor에 asof=오늘 스냅샷을
# upsert한다 → 최근 MonitorSnapshot.asof_date가 refresh 성공의 관측 가능한 흔적.
# 최근 2 거래일 내 성공 기록을 요구하되, 주말·연휴는 임계(달력일)로 흡수(zero-noise).
# check_issuance_log_freshness와 동일한 방어 패턴(Django lazy setup + OK-skip).

# 2 거래일 ≈ 주말(2) 흡수해 5 달력일. issuance 관례(ISSUANCE_STALE_DAYS=5)와 정합.
MONITOR_REFRESH_STALE_DAYS = 5


def check_monitor_refresh_freshness() -> CheckResult:
    """최근 MonitorSnapshot(=refresh 태스크 성공 흔적) 신선도. [MON-P2-BEAT §6]

    - 비-런타임/DB 미가용 → OK-skip(노이즈 0).
    - stock scope Monitor 0건(관제 대상 없음) → OK-skip.
    - Monitor 있으나 스냅샷 이력 0 / 최근 asof가 임계 초과 → WARN(태스크 미실행·skip 누적 의심).
    """
    name = "monitor refresh 신선도"
    try:
        import os

        import django

        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
        from apps.monitor.models import Monitor, MonitorSnapshot
    except Exception as e:  # noqa: BLE001 — 비-런타임 환경은 검사 대상 아님
        return CheckResult(
            name=name,
            status=OK,
            detail="Django/DB 미가용 — 검사 생략(비-런타임 환경)",
            evidence=[str(e)[:120]],
        )

    try:
        has_stock = Monitor.objects.filter(scope="stock").exists()
        latest = MonitorSnapshot.objects.order_by("-asof_date").first()
    except Exception as e:  # noqa: BLE001 — 테이블 부재 등
        return CheckResult(
            name=name,
            status=WARN,
            detail="MonitorSnapshot 조회 실패 — 테이블 부재 가능",
            evidence=[str(e)[:120]],
        )

    if not has_stock:
        return CheckResult(
            name=name,
            status=OK,
            detail="stock scope Monitor 0건 — 검사 생략(관제 대상 없음)",
        )
    if latest is None:
        return CheckResult(
            name=name,
            status=WARN,
            detail="Monitor 있으나 스냅샷 이력 0건 — refresh 미실행 의심",
        )

    age_days = (datetime.now().date() - latest.asof_date).days
    if age_days > MONITOR_REFRESH_STALE_DAYS:
        return CheckResult(
            name=name,
            status=WARN,
            detail=(
                f"최근 refresh {age_days}일 전({latest.asof_date}) — 임계 "
                f"{MONITOR_REFRESH_STALE_DAYS}일 초과(태스크 미실행/skip 누적 의심)"
            ),
        )
    return CheckResult(
        name=name,
        status=OK,
        detail=f"최근 refresh asof {latest.asof_date} (age {age_days}일 ≤ {MONITOR_REFRESH_STALE_DAYS})",
    )


# ── (15) stale pending 백-어노테이션 검문 (MGMT-HARDEN, common-bugs #52) ──────
# D2 phantom 교훈: 해소된 결정이 구 pending(⏸️) 블록 미갱신으로 stale 잔존 → 인계로 무검증 전파.
# 판정: PROGRESS.md의 ⏸️(paused) 상태 블록 중, 해소 델타(→ RESOLVED/LANDED/SUPERSEDED 등)
#       없이 타임스탬프가 PENDING_STALE_DAYS(3 거래일 근사 = 달력 3일) 초과 방치 → WARN.
# WARN-only(FAIL 아님. 1주 클린 후 FAIL 승격은 별도 — 지금 승격 금지).
# TASKQUEUE 제외: 큐는 설계상 장기 pending(💤/🕓 트리거 게이트) 보유 — ⏸️ 미사용이라 오탐 원천.
# 거래일 캘린더 = issuance/execution-tree의 "달력일 임계로 주말 흡수" 관례 재사용(엄밀 NYSE 캘린더 부재).
PENDING_STALE_DAYS = 3
PENDING_MARKER = "⏸️"
PENDING_DELTA_MARKERS = ("RESOLVED", "LANDED", "SUPERSEDED", "해소 델타", "소화됨", "해소됨")

# [C] HEALTH-STALE-FAIL-PROMOTE 트리거 — 이 날짜부터 '순수 stale'(비-blocked)만 WARN→FAIL 승격.
# 승격은 today 게이트(순수함수 파라미터화 관례) — 테스트는 today를 주입해 승격 전/후 양방향 검증.
STALE_FAIL_PROMOTE_DATE = datetime(2026, 7, 20).date()

# blocked(외부 의존) 표기 문법 — 단일 출처 = D-HEALTH-BLOCKED-DISTINCTION (MGMT-BATCH-11 적용).
# blocked(dep=<TASK_ID>) 항목은 FAIL 승격 제외(WARN 유지), 단 dep가 TASKQUEUE 실존해야 유효.
_BLOCKED_RE = re.compile(r"blocked\(dep=([A-Za-z0-9][A-Za-z0-9_\-]*)\)")


def _scan_stale_pending(text: str, today) -> list[tuple[str, int, str | None]]:
    """⏸️ + 날짜 有 + 해소델타 無 + age > 임계 인 블록을 (헤더요약, age, blocked_dep) 리스트로 반환.

    blocked_dep = `blocked(dep=<ID>)` 표기의 ID(없으면 None). 순수 함수(DB·git 접근 0)
    → 합성 픽스처로 양방향 검증 가능. today = datetime.date.
    """
    stale: list[tuple[str, int, str | None]] = []
    for line in text.splitlines():
        if PENDING_MARKER not in line:
            continue
        if any(mk in line for mk in PENDING_DELTA_MARKERS):
            continue  # 해소 델타 부기됨 → 정상(백-어노테이션 완료, WARN 억제)
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", line)
        if not m:
            continue
        try:
            block_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        except ValueError:
            continue
        age = (today - block_date).days
        if age > PENDING_STALE_DAYS:
            hm = re.search(r"\*\*(.+?)\*\*", line)
            head = (hm.group(1) if hm else line.strip())[:70]
            bm = _BLOCKED_RE.search(line)
            stale.append((head, age, bm.group(1) if bm else None))
    return stale


def _taskqueue_has_task_id(tq_text: str, task_id: str) -> bool:
    """dep=<TASK_ID>가 TASKQUEUE 표의 **정의 행**(첫 칸 셀)로 실존하는지.

    프로즈 언급·타 행의 참조와 구분하기 위해 `^| <ID> |` 정의 행만 인정(남용 방지).
    """
    return re.search(r"(?m)^\|\s*" + re.escape(task_id) + r"\s*\|", tq_text) is not None


def evaluate_stale_pending(progress_text: str, tq_text: str, today) -> CheckResult:
    """stale pending 판정(순수함수 — 파일/시계 미접근, today·텍스트 주입).

    blocked(dep=<ID>) + dep 실존 → WARN 유지(FAIL 승격 제외).
    blocked이나 dep 미실존 → **무효**: 일반 stale 규칙 적용 + 무효 경고 별도 표시.
    비-blocked 순수 stale → today ≥ 승격일이면 FAIL, 아니면 WARN.
    """
    name = "stale pending 백-어노테이션"
    stale = _scan_stale_pending(progress_text, today)
    if not stale:
        return CheckResult(
            name=name,
            status=OK,
            detail=f"⏸️ 해소 델타 없는 stale pending 0건 (임계 {PENDING_STALE_DAYS} 거래일, PROGRESS)",
        )

    promoted = today >= STALE_FAIL_PROMOTE_DATE
    valid_blocked: list[tuple[str, int, str]] = []
    invalid_blocked: list[tuple[str, int, str]] = []
    pure: list[tuple[str, int]] = []
    for head, age, dep in stale:
        if dep is None:
            pure.append((head, age))
        elif _taskqueue_has_task_id(tq_text, dep):
            valid_blocked.append((head, age, dep))
        else:
            invalid_blocked.append((head, age, dep))

    # 무효 blocked = 일반 stale 취급(승격 대상) — dep 실존 검증 실패 시 부기 회피 차단.
    effective_pure = pure + [(h, a) for h, a, _ in invalid_blocked]

    evidence: list[str] = []
    for h, a, dep in valid_blocked:
        evidence.append(f"{h} (age {a}일) — blocked(dep={dep}) 유효 → WARN 유지·[C] FAIL 승격 제외")
    for h, a, dep in invalid_blocked:
        evidence.append(
            f"{h} (age {a}일) — ⚠ 무효 blocked(dep={dep} = TASKQUEUE 미실존) → 일반 stale 적용"
        )
    for h, a in pure:
        evidence.append(f"{h} (age {a}일) — 순수 stale (→ RESOLVED/LANDED/SUPERSEDED 부기 필요)")

    status = ERROR if (effective_pure and promoted) else WARN

    parts: list[str] = []
    if effective_pure:
        verb = "FAIL(승격됨)" if promoted else "WARN(승격 전)"
        parts.append(f"순수 stale {len(effective_pure)}건 → {verb} (부기 필요, #52)")
    if valid_blocked:
        parts.append(f"blocked(외부 의존) {len(valid_blocked)}건 → WARN 유지(승격 제외)")
    if invalid_blocked:
        parts.append(f"⚠ 무효 blocked 표기 {len(invalid_blocked)}건 (dep TASKQUEUE 미실존)")
    detail = " · ".join(parts) + f" [임계 {PENDING_STALE_DAYS}거래일 · 승격일 {STALE_FAIL_PROMOTE_DATE}]"
    return CheckResult(name=name, status=status, detail=detail, evidence=evidence)


def check_stale_pending_backannotation() -> CheckResult:
    progress = PROGRESS_MD.read_text(encoding="utf-8") if PROGRESS_MD.exists() else ""
    tq = TASKQUEUE_MD.read_text(encoding="utf-8") if TASKQUEUE_MD.exists() else ""
    return evaluate_stale_pending(progress, tq, datetime.now().date())


# ── main runner ─────────────────────────────────────────────────────────────


CHECKS = [
    check_origin_main_hash,
    check_brunch_worktree_existence,
    check_progress_staleness,
    check_taskqueue_done_matching,
    check_taskqueue_claim_vs_evidence,
    check_decisions_freshness,
    check_slice_branches_unmerged,
    check_external_automation_commits,
    check_shared_boundary,
    check_llm_direct_call_boundary,
    check_known_test_fails,
    check_issuance_log_freshness,
    check_execution_tree_alignment,
    check_monitor_refresh_freshness,
    check_stale_pending_backannotation,
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
