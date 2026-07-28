"""OPS-WORKTREE-ISOLATION Phase 3 — verify 무인 감시 편입용 순수 점검 함수 + 수집 헬퍼.

verify_pair_aggregation.py(02:30)가 import해 section D로 편입한다.
순수 함수(check_*)는 django 무의존 → tests/ops/test_verify_ops_checks.py로 mock 테스트.

설계 원칙(무인 파수꾼 — 오탐·침묵결함 금지):
- 반환 severity = "ok"|"info"|"warn"|"skip". verify는 "warn"만 WARN으로 승격(FAIL 절대 없음 = 상한 WARN).
- 입력 미확인 시 "skip"(정보성) — 절대 오탐 WARN 만들지 않음.
- 드리프트는 "HEAD==tip 정확일치"가 아니라 **조상 기반**: main은 상시 전진하므로 뒤처짐(조상)=정상 lag,
  계보 밖(diverged)만 WARN(07-04 hijack/stuck 시그니처). 오탐 방지(지시서 §6·⑴ 최우선).
"""

import subprocess
from pathlib import Path

MARKER_NAME = ".session-marker"
MARKER_TTL_HOURS = 24
WORKER_TREE = Path.home() / "worktrees" / "sv-worker-runtime"
# stale 마커 스캔 대상(세션 트리 후보). 런타임 트리는 마커 대상 아님(R1) — 스캔 제외.
_SCAN_ROOTS = [Path.home() / "worktrees", Path.home() / "Desktop"]
_RUNTIME_TREES = {
    str(Path.home() / "worktrees" / "sv-worker-runtime"),
    str(Path.home() / "worktrees" / "sv-web-runtime"),
    str(Path.home() / "worktrees" / "sv-api-runtime"),
}


# ─────────────────── 순수 점검 함수 (mock 테스트) ───────────────────

def check_worker_tree_drift(head, origin, is_ancestor):
    """워커 트리 정합. is_ancestor = head가 origin/main 조상인가(None=미확인)."""
    if not head or not origin:
        return "skip", "worker tree drift: HEAD/origin 미확인 — skip"
    if head == origin:
        return "ok", None
    if is_ancestor:  # 뒤처졌으나 main 계보 내 = 정상 lag(다음 sv sync서 정합)
        return "info", f"worker tree 정상 lag: HEAD={head[:7]}<origin/main={origin[:7]}(조상)"
    return "warn", (
        f"[ALERT] worker tree drift: HEAD={head[:7]}가 origin/main({origin[:7]}) "
        "계보 밖(diverged) — 수동 체크아웃/hijack 의심(07-04류). sv sync로 재정합 필요"
    )


def check_stale_markers(stale_list):
    """stale_list = [(tree, age_h), ...](>=TTL) / None=스캔실패."""
    if stale_list is None:
        return "skip", "stale 마커 스캔 실패 — skip"
    if not stale_list:
        return "ok", None
    items = ", ".join(f"{t}({a}h)" for t, a in stale_list)
    return "warn", (
        f"[ALERT] stale 마커 {len(stale_list)}건(>{MARKER_TTL_HOURS}h): {items} — "
        "Phase1 heal 미작동/고아 세션 의심(수동 정리 검토)"
    )


def check_code_version(worker_start_epoch, head_commit_epoch):
    """워커 프로세스 기동시각 vs 트리 HEAD 커밋시각. HEAD 커밋이 더 최근 → 헌 코드 서빙."""
    if worker_start_epoch is None or head_commit_epoch is None:
        return "skip", "코드버전: 워커 기동시각/HEAD 커밋시각 미확인 — skip"
    if head_commit_epoch > worker_start_epoch:
        return "warn", (
            f"[ALERT] 워커 코드버전 괴리: 트리 HEAD 커밋({head_commit_epoch})이 "
            f"워커 기동({worker_start_epoch}) 이후 — 재기동 누락(헌 코드 서빙) 의심. "
            "launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-worker"
        )
    return "ok", None


# ─────────────────── 수집 헬퍼 (I/O — 실패 시 None, graceful) ───────────────────

def _git(args, cwd=WORKER_TREE):
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd)] + args,
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _worker_start_epoch():
    """celery-worker launchd 프로세스 기동 epoch(초). 실패 시 None."""
    try:
        out = subprocess.run(
            ["launchctl", "list"], capture_output=True, text=True, timeout=10
        ).stdout
        pid = None
        for ln in out.splitlines():
            if "com.stockvis.celery-worker" in ln and "neo4j" not in ln:
                first = ln.split("\t")[0].strip()
                if first and first != "-":
                    pid = first
                break
        if not pid:
            return None
        lstart = subprocess.run(
            ["ps", "-o", "lstart=", "-p", pid], capture_output=True, text=True, timeout=10
        ).stdout.strip()
        if not lstart:
            return None
        # "Mon Jul 20 14:29:33 2026" → epoch (date -j -f, macOS)
        ep = subprocess.run(
            ["date", "-j", "-f", "%a %b %d %H:%M:%S %Y", lstart, "+%s"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return int(ep) if ep.isdigit() else None
    except Exception:
        return None


def _scan_stale_markers(now_epoch):
    """세션 트리 마커 스캔 → [(tree, age_h)] (age>=TTL). 런타임 트리 제외. 실패 시 None."""
    try:
        stale = []
        for root in _SCAN_ROOTS:
            if not root.is_dir():
                continue
            for mp in root.glob(f"*/{MARKER_NAME}"):
                tree = str(mp.parent)
                if tree in _RUNTIME_TREES:
                    continue
                created = _marker_created_epoch(mp)
                if created is None:
                    stale.append((tree, "불량"))  # created 없음 = stale 취급
                    continue
                age_h = (now_epoch - created) // 3600
                if age_h >= MARKER_TTL_HOURS:
                    stale.append((tree, age_h))
        return stale
    except Exception:
        return None


def _marker_created_epoch(marker_path):
    try:
        import json
        data = json.loads(Path(marker_path).read_text())
        v = str(data.get("created_at", ""))
        return int(v) if v.isdigit() else None
    except Exception:
        return None


def gather(now_epoch):
    """section D 입력 수집(전 항목 wrapped — 실패는 None으로 격리)."""
    head = _git(["rev-parse", "HEAD"])
    origin = _git(["rev-parse", "origin/main"])
    is_ancestor = None
    if head and origin:
        try:
            rc = subprocess.run(
                ["git", "-C", str(WORKER_TREE), "merge-base", "--is-ancestor", head, origin],
                capture_output=True, timeout=10,
            ).returncode
            is_ancestor = (rc == 0)
        except Exception:
            is_ancestor = None
    hc = _git(["show", "-s", "--format=%ct", "HEAD"])
    head_commit = int(hc) if hc and hc.isdigit() else None
    return {
        "head": head, "origin": origin, "is_ancestor": is_ancestor,
        "head_commit": head_commit,
        "worker_start": _worker_start_epoch(),
        "stale_markers": _scan_stale_markers(now_epoch),
    }


def run_all(now_epoch):
    """3항목 실행 → [(severity, msg)]. verify가 이것만 호출(예외는 verify가 격벽)."""
    d = gather(now_epoch)
    return [
        check_worker_tree_drift(d["head"], d["origin"], d["is_ancestor"]),
        check_stale_markers(d["stale_markers"]),
        check_code_version(d["worker_start"], d["head_commit"]),
    ]
