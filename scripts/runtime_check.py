#!/usr/bin/env python3
"""runtime_check.py — 런타임 3종 read-only 감지 (RB-1 / D-RB-1).

**100% read-only.** 프로세스 kill·kickstart·checkout·쓰기(자체 로그 append 제외)를
절대 하지 않는다. 감지·판정·기록만 한다 — 설계 사상 "감지는 자동, 집행은 사람".
자동 집행이 필요해 보이면 그 검사를 빼고 사람에게 보고한다.

검사 3종 (인벤토리 RUNTIME_INVENTORY 각 항목):
  ⑴ 고아 스윕  — 포트 리스너 pid가 launchd 관리 pid 자신/자손이 아니면 ORPHAN
                 (관리이탈 고아가 포트 점유 = 스테일 런타임 3건 공통 근인, #116/#45).
  ⑵ 드리프트   — 런타임 트리 HEAD vs origin/main behind 커밋 수(git fetch = read-only).
                 behind>0 = DRIFT 기록, 24h 지속 = WARN(활성 세션의 순간 드리프트는 정상).
  ⑶ launchd    — 대상 서비스 로드·구동 여부(미로드=ERROR, 로드했으나 미구동=WARN).

인벤토리(트리·포트·라벨)는 **이 파일의 RUNTIME_INVENTORY가 단일 출처**이며,
런북(docs/runbook/DEPLOY.md 부록)은 이 상수를 참조 표기한다(복제 drift 방지).

출력 이원화:
  - 사람용: pass/warn/fail 요약 테이블(health_check 관례).
  - 기계용: runtime_check.log에 JSON 1줄 append(시각·판정·상세) — 드리프트 지속 판정과
           health_check.py 표면화의 소스.

종료 코드: 0=전부 OK, 1=WARN 존재, 2=ERROR(ORPHAN 포함) 존재. 알림은 래퍼
(scripts/runtime-check.sh)가 이 코드로 결정 — 이 스크립트는 발송하지 않는다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── 상태 코드 (health_check.py와 동일 관례) ──────────────────────────────
OK = 0
WARN = 1
ERROR = 2
STATUS_LABEL = {OK: "✅ OK", WARN: "⚠  WARN", ERROR: "❌ ERROR"}

HOME = Path.home()
WORKTREES = HOME / "worktrees"
LOG_DIR = HOME / "Library" / "Logs" / "stockvis"
RUNTIME_CHECK_LOG = LOG_DIR / "runtime_check.log"
DRIFT_WARN_HOURS = 24.0

# ── 런타임 인벤토리 = 단일 출처 (런북 부록이 이것을 참조) ──────────────────
# name: 표시명 / tree: 런타임 트리 경로 / port: 서빙 포트(None=포트 없음) /
# label: launchd 라벨. 새 런타임 추가 시 여기에만 추가한다.
RUNTIME_INVENTORY: list[dict] = [
    {"name": "worker", "tree": str(WORKTREES / "sv-worker-runtime"), "port": None, "label": "com.stockvis.celery-worker"},
    {"name": "beat", "tree": str(WORKTREES / "sv-worker-runtime"), "port": None, "label": "com.stockvis.celery-beat"},
    {"name": "web", "tree": str(WORKTREES / "sv-web-runtime"), "port": 3000, "label": "com.stockvis.web-frontend"},
    {"name": "api", "tree": str(WORKTREES / "sv-api-runtime"), "port": 18765, "label": "com.stockvis.web"},
]
# neo4j 워커(OPS-NEO4J-TREE)는 **알려진 예외** — 미커밋 recon 트리 구동이 별건으로
# 등재돼 있어 인벤토리에서 의도적으로 제외(런북 부록에 예외 명기).


@dataclass
class CheckResult:
    name: str
    status: int
    detail: str
    evidence: list[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════════════
# 순수 판정 함수 (단위 테스트 대상 — IO 없음)
# ════════════════════════════════════════════════════════════════════════

def classify_orphan(
    port: int | None,
    listener_pid: int | None,
    launchd_pid: int | None,
    listener_is_descendant_of_launchd: bool,
) -> tuple[int, str]:
    """포트 리스너가 launchd 관리 프로세스(자신/자손)인지 판정.

    - port None: 포트 없는 서비스 → 고아 검사 비대상(OK).
    - listener 없음: 포트 미청취 → 고아 아님(다운 여부는 launchd 검사 담당) → OK.
    - listener == launchd_pid(예: exec daphne) 또는 listener가 launchd_pid의 자손
      (예: npm 부모 → next 자식): 정상 관리(OK).
    - 그 외(관리이탈 프로세스가 포트 점유): ORPHAN(ERROR).
    """
    if port is None:
        return OK, "포트 없음(고아 검사 비대상)"
    if listener_pid is None:
        return OK, f":{port} 리스너 없음(다운 여부는 launchd 검사)"
    if launchd_pid is not None and listener_pid == launchd_pid:
        return OK, f":{port} 리스너 pid={listener_pid} = launchd 관리 pid(정상)"
    if listener_is_descendant_of_launchd:
        return OK, f":{port} 리스너 pid={listener_pid} = launchd({launchd_pid}) 자손(정상)"
    return ERROR, (
        f"ORPHAN — :{port} 리스너 pid={listener_pid}가 launchd 관리 pid={launchd_pid}의 "
        f"자신/자손이 아님(관리이탈 고아 포트 점유). 런북 1장 절차로 처리(집행=사람)."
    )


def classify_drift(behind: int, drift_age_hours: float | None) -> tuple[int, str]:
    """런타임 트리가 origin/main 대비 뒤처진 정도 판정.

    - behind==0: 정합(OK).
    - behind>0 & 지속<24h(또는 최초 감지): DRIFT 기록하되 OK(활성 세션 순간 드리프트=정상).
    - behind>0 & 지속>=24h: WARN(수일 무동기 = 스테일 런타임 징후).
    """
    if behind <= 0:
        return OK, "origin/main 정합"
    if drift_age_hours is not None and drift_age_hours >= DRIFT_WARN_HOURS:
        return WARN, f"DRIFT {behind}커밋 뒤처짐·{drift_age_hours:.1f}h 지속(>=24h) — 랜딩 동기 필요"
    age_str = f"{drift_age_hours:.1f}h" if drift_age_hours is not None else "최초 감지"
    return OK, f"DRIFT {behind}커밋 뒤처짐·{age_str}(<24h, 활성 세션 정상 범위)"


def classify_launchd(loaded: bool, has_pid: bool) -> tuple[int, str]:
    """launchd 서비스 로드·구동 판정."""
    if not loaded:
        return ERROR, "launchd 미로드(job 부재) — bootstrap 필요"
    if not has_pid:
        return WARN, "launchd 로드됐으나 미구동(pid 없음) — 크래시/백오프 가능"
    return OK, "launchd 로드·구동"


def drift_age_from_history(history: list[tuple[str, int]], now: datetime) -> float | None:
    """runtime_check.log에서 읽은 (iso_ts, behind) 이력으로 드리프트 지속 시간 산출.

    최근→과거로 훑어 behind>0가 연속된 최초 시점을 찾는다. 직전에 behind==0이 있으면
    거기서 리셋(현재 드리프트 구간의 시작만 센다). 이력 없거나 현재 정합이면 None.
    history는 오름차순(과거→현재) 가정.
    """
    if not history:
        return None
    # 현재(마지막)가 드리프트가 아니면 지속 시간 없음
    if history[-1][1] <= 0:
        return None
    # 뒤에서부터 연속 drift 구간의 시작 timestamp를 찾는다
    start_ts = history[-1][0]
    for ts, behind in reversed(history):
        if behind <= 0:
            break
        start_ts = ts
    try:
        start = datetime.fromisoformat(start_ts)
    except (ValueError, TypeError):
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    delta = now - start
    return max(0.0, delta.total_seconds() / 3600.0)


# ════════════════════════════════════════════════════════════════════════
# IO 함수 (subprocess — 전부 read-only 조회)
# ════════════════════════════════════════════════════════════════════════

def _run(args: list[str], timeout: int = 15) -> str:
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return out.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return ""


def port_listener_pid(port: int) -> int | None:
    """lsof로 포트 LISTEN pid 조회(read-only)."""
    out = _run(["lsof", f"-ti:{port}", "-sTCP:LISTEN"])
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    return None


def process_ppid(pid: int) -> int | None:
    out = _run(["ps", "-o", "ppid=", "-p", str(pid)])
    out = out.strip()
    return int(out) if out.isdigit() else None


def is_descendant(pid: int | None, ancestor: int | None, max_depth: int = 12) -> bool:
    """pid의 ppid 계보에 ancestor가 있는지(read-only ps 순회)."""
    if pid is None or ancestor is None:
        return False
    cur = pid
    for _ in range(max_depth):
        parent = process_ppid(cur)
        if parent is None or parent <= 1:
            return False
        if parent == ancestor:
            return True
        cur = parent
    return False


def launchd_pid(label: str) -> int | None:
    """launchctl print에서 관리 pid 조회(read-only)."""
    out = _run(["launchctl", "print", f"gui/{os.getuid()}/{label}"])
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("pid = "):
            frag = s[len("pid = "):].strip()
            if frag.isdigit():
                return int(frag)
    return None


def launchd_loaded(label: str) -> bool:
    out = _run(["launchctl", "print", f"gui/{os.getuid()}/{label}"])
    return bool(out) and "could not find service" not in out.lower()


def tree_behind_count(tree: str) -> int | None:
    """런타임 트리 HEAD가 origin/main 대비 몇 커밋 뒤처졌나(fetch=read-only)."""
    if not Path(tree).is_dir():
        return None
    # fetch는 원격 조회일 뿐(트리 변경 없음). 실패해도 캐시된 origin/main으로 진행.
    _run(["git", "-C", tree, "fetch", "origin", "main", "--quiet"], timeout=30)
    out = _run(["git", "-C", tree, "rev-list", "--count", "HEAD..origin/main"])
    return int(out) if out.strip().isdigit() else None


def read_drift_history(tree_name: str, log_path: Path = RUNTIME_CHECK_LOG) -> list[tuple[str, int]]:
    """runtime_check.log에서 해당 트리의 (iso_ts, behind) 이력 추출(오름차순)."""
    if not log_path.exists():
        return []
    hist: list[tuple[str, int]] = []
    try:
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = rec.get("ts")
            item = rec.get("items", {}).get(tree_name)
            if ts and item is not None and "behind" in item and item["behind"] is not None:
                hist.append((ts, int(item["behind"])))
    except OSError:
        return []
    return hist


# ════════════════════════════════════════════════════════════════════════
# 검사 실행 (IO + 판정 조합)
# ════════════════════════════════════════════════════════════════════════

def check_item(item: dict, now: datetime) -> tuple[CheckResult, dict]:
    """인벤토리 1항목에 대해 3검사 수행. (표시용 결과, 로그용 dict) 반환."""
    name = item["name"]
    port = item["port"]
    label = item["label"]
    tree = item["tree"]

    # ⑶ launchd
    loaded = launchd_loaded(label)
    lpid = launchd_pid(label) if loaded else None
    st_launchd, dt_launchd = classify_launchd(loaded, lpid is not None)

    # ⑴ 고아
    lis_pid = port_listener_pid(port) if port else None
    desc = is_descendant(lis_pid, lpid) if (lis_pid and lpid and lis_pid != lpid) else False
    st_orphan, dt_orphan = classify_orphan(port, lis_pid, lpid, desc)

    # ⑵ 드리프트
    behind = tree_behind_count(tree)
    if behind is None:
        st_drift, dt_drift = OK, "트리 부재/조회 불가(드리프트 검사 생략)"
    else:
        # 이번 실행분을 포함해 지속시간 산출(현재 behind를 이력 끝에 가정)
        hist = read_drift_history(name)
        hist_with_now = hist + [(now.isoformat(), behind)]
        age = drift_age_from_history(hist_with_now, now)
        st_drift, dt_drift = classify_drift(behind, age)

    overall = max(st_launchd, st_orphan, st_drift)
    details = f"launchd: {dt_launchd} / 고아: {dt_orphan} / 드리프트: {dt_drift}"
    evidence = [
        f"label={label} launchd_pid={lpid} loaded={loaded}",
        f"port={port} listener_pid={lis_pid} descendant={desc}",
        f"tree_behind={behind}",
    ]
    log_item = {
        "status": overall,
        "launchd": {"loaded": loaded, "pid": lpid, "status": st_launchd},
        "orphan": {"listener_pid": lis_pid, "status": st_orphan},
        "behind": behind,
        "drift_status": st_drift,
    }
    return CheckResult(name=name, status=overall, detail=details, evidence=evidence), log_item


def run_all() -> tuple[list[CheckResult], dict]:
    now = datetime.now(timezone.utc)
    results: list[CheckResult] = []
    log_items: dict = {}
    for item in RUNTIME_INVENTORY:
        res, log_item = check_item(item, now)
        results.append(res)
        log_items[item["name"]] = log_item
    overall = max((r.status for r in results), default=OK)
    log_record = {"ts": now.isoformat(), "overall": overall, "items": log_items}
    return results, log_record


def append_log(record: dict, log_path: Path = RUNTIME_CHECK_LOG) -> None:
    """기계용 로그 1줄 append (유일하게 허용된 쓰기). 실패는 비차단."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[runtime_check] ⚠ 로그 기록 실패(비차단): {e}", file=sys.stderr)


def print_summary(results: list[CheckResult], overall: int) -> None:
    print("=" * 72)
    print("runtime_check — 런타임 3종 read-only 감지 (RB-1)")
    print("=" * 72)
    for r in results:
        print(f"{STATUS_LABEL[r.status]}  [{r.name}] {r.detail}")
    n_ok = sum(1 for r in results if r.status == OK)
    n_warn = sum(1 for r in results if r.status == WARN)
    n_err = sum(1 for r in results if r.status == ERROR)
    print("-" * 72)
    print(f"요약: {n_ok} OK / {n_warn} WARN / {n_err} ERROR → 종합 {STATUS_LABEL[overall]}")


def main() -> int:
    results, record = run_all()
    append_log(record)
    print_summary(results, record["overall"])
    return record["overall"]


if __name__ == "__main__":
    sys.exit(main())
