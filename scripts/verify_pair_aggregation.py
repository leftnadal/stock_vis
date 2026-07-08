#!/usr/bin/env python3
"""chainsight-pair-aggregation 자율 틱 검증 (#28 Gate 2 관찰 — 로컬 전용).

beat 자율 틱(America/New_York 11:30 매일)이 RelationPairSnapshot을 스스로 적립하는지를
로컬 dev 자원(launchctl 프로세스 / celery 로그 / dev DB)으로 점검한다.
cloud routine은 이 자원에 접근 못 하므로 이 스크립트는 로컬 실행 전용이다.

권장 실행: 매일 02:30 KST(11:30 ET 틱 +버퍼). launchd StartCalendarInterval 또는 수동.

검증 절차:
    PRE  celery-beat/worker 프로세스 생존 (죽었으면 재기동 필요 = 고장 아님, false negative 차단)
    A    worker 로그에 최근 aggregate_relation_pairs "succeeded"·"unregistered task" 흔적
    B    RelationPairSnapshot period 정합 — 최신 period가 오늘/어제, count 밴드, 중복(≈2배) 없음, 궤적 누적

판정: PASS(발화·적립 정상) / WARN(프로세스 미기동 등 재관찰) / FAIL(unregistered·중복·미적립)
출력: 콘솔 + exit code (0=PASS, 1=WARN, 2=FAIL)

실행:
    python scripts/verify_pair_aggregation.py
    python scripts/verify_pair_aggregation.py --quiet   # 판정 라인만
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# repo 루트를 import 경로에 추가 (scripts/ 하위에서 실행돼도 config 패키지 발견)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db.models import Count, Max  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.chain_sight.models import RelationPairSnapshot  # noqa: E402

LOGDIR = Path.home() / "Library/Logs/stockvis"
# 쌍 수는 관계 그래프 규모에 따라 변동 → 하한/상한 밴드로 판단(정확한 9562 고정 금지).
COUNT_LOW, COUNT_HIGH = 5_000, 15_000
DUP_FACTOR = 1.8  # 최신 period가 밴드 상한×이 배수 이상이면 append 중복 의심


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
    except Exception as exc:  # pragma: no cover
        return f"<error: {exc}>"


def pre_check():
    """PRE — beat/worker launchd 프로세스 생존. (PID '-' = 미기동)"""
    out = _run(["launchctl", "list"])
    beat_alive = worker_alive = False
    for line in out.splitlines():
        if "com.stockvis.celery-beat" in line:
            beat_alive = not line.split("\t")[0].strip().startswith("-")
        if "com.stockvis.celery-worker" in line and "neo4j" not in line:
            worker_alive = not line.split("\t")[0].strip().startswith("-")
    return beat_alive, worker_alive


def log_check(boundary):
    """A — worker 로그에서 aggregate 태스크의 boundary 이후 succeeded/unregistered 집계.

    tail 고정창(구 [-5000:]) 대신 grep으로 매칭 라인만 전수 스캔 → 로그 폭주 시
    성공 증거가 창 밖으로 스크롤아웃돼 발생하던 오탐(2026-07-03 사건)을 차단한다.
    전수 스캔의 부작용(이미 해소된 과거 unregistered 부활)은 boundary 이전 라인 제외로 봉인.
    """
    succeeded = unregistered = 0
    for name in ("celery-worker.log", "celery-worker-error.log"):
        p = LOGDIR / name
        if not p.exists():
            continue
        out = _run(["grep", "-a", "aggregate_relation_pairs", str(p)])
        if out.startswith("<error"):
            continue
        for ln in out.splitlines():
            if "succeeded" not in ln and "unregistered" not in ln.lower():
                continue
            m = _TS_RE.search(ln)
            if not m:
                continue
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=_LOG_TZ
            )
            if ts < boundary:
                continue
            if "succeeded" in ln:
                succeeded += 1
            elif "unregistered" in ln.lower():
                unregistered += 1
    return succeeded, unregistered


def db_check():
    """B — period 분포. (최신 period 신선도 + count 밴드 + 중복 없음)"""
    rows = list(
        RelationPairSnapshot.objects.values("period")
        .annotate(n=Count("id"))
        .order_by("period")
    )
    latest = RelationPairSnapshot.objects.aggregate(mx=Max("period"))["mx"]
    return rows, latest


# --- 직전 자율 틱 완주 검증 (PR ops v2 §4) ---
# RelationPairSnapshot은 upsert형((canonical_a,canonical_b,period) unique) + updated_at 부재 →
# 같은 period 재실행은 count·타임스탬프 불변. 따라서 "직전 11:30 ET 틱 이후 succeeded 로그"가
# 유일한 양성 발화 증거(watchdog=프로세스 생존과 별개 = 태스크 완주). KeepAlive의 맹점(crash-loop) 가시화.
_ET = ZoneInfo("America/New_York")
_LOG_TZ = ZoneInfo("Asia/Seoul")  # celery 로그 타임스탬프 = 시스템 로컬(실측). tz 정합 리스크(PR §6).
_TS_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def last_et_tick_boundary(now_et=None):
    """직전 11:30 ET 경계 (DST 자동)."""
    now_et = (now_et or datetime.now(_ET)).astimezone(_ET)
    b = now_et.replace(hour=11, minute=30, second=0, microsecond=0)
    return b if now_et >= b else b - timedelta(days=1)


def check_last_tick_succeeded(boundary, succeeded):
    """직전 11:30 ET 틱 경계 이후 aggregate succeeded 존재 여부. (ok, boundary, msg).

    succeeded = log_check가 동일 boundary 기준으로 전수 스캔한 성공 건수(별도 재스캔 없음).
    upsert형이라 로그가 유일한 양성 발화 증거 — grep 전수 스캔이라 로그 폭주에도 누락 없음.
    """
    if succeeded > 0:
        return True, boundary, f"직전 틱({boundary:%Y-%m-%d %H:%M %Z}) 이후 succeeded 확인"
    return False, boundary, (
        f"[ALERT] 직전 자율 틱({boundary:%Y-%m-%d %H:%M %Z}) 이후 succeeded 로그 없음 — "
        "프로세스 생존(watchdog OK)해도 틱 미발화/실패 의심. "
        "worker 로그 확인 → 필요 시 launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-worker"
    )


def main():
    quiet = "--quiet" in sys.argv
    today = timezone.now().date()
    boundary = last_et_tick_boundary()
    beat_alive, worker_alive = pre_check()
    succeeded, unregistered = log_check(boundary)
    rows, latest = db_check()

    verdict = "PASS"
    notes = []

    # PRE
    if not beat_alive or not worker_alive:
        verdict = "WARN"
        notes.append(
            f"프로세스 미기동(beat={beat_alive}, worker={worker_alive}) → "
            f"launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-{'beat' if not beat_alive else 'worker'} 후 재관찰(고장 아님)"
        )

    # A
    if unregistered:
        verdict = "FAIL"
        notes.append(
            f"직전 틱 경계 이후 unregistered {unregistered}건 → 신규 task 미등록. "
            "worker 재시작 필수: launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-worker"
        )

    # B
    if latest is None:
        verdict = "FAIL"
        notes.append("RelationPairSnapshot 0행 → 적립 없음. migrate 0014 적용 + beat/worker 확인.")
    else:
        latest_n = next((r["n"] for r in rows if r["period"] == latest), 0)
        stale_days = (today - latest).days
        if stale_days > 1:
            verdict = "FAIL" if verdict != "FAIL" else verdict
            notes.append(f"최신 period {latest}가 {stale_days}일 stale → 자율 틱 미적립(스케줄 점검).")
        if latest_n > COUNT_HIGH * DUP_FACTOR:
            verdict = "FAIL"
            notes.append(f"period {latest} count={latest_n} 과다 → append 중복 의심(멱등성 깨짐, dedup 필요).")
        elif not (COUNT_LOW <= latest_n <= COUNT_HIGH):
            if verdict == "PASS":
                verdict = "WARN"
            notes.append(f"period {latest} count={latest_n}가 밴드[{COUNT_LOW},{COUNT_HIGH}] 밖 → 규모 확인.")

    # C — 직전 자율 틱 완주 (crash-loop/미발화 가시화, upsert형이라 로그가 유일 증거)
    tick_ok, tick_boundary, tick_msg = check_last_tick_succeeded(boundary, succeeded)
    if not tick_ok:
        if verdict == "PASS":
            verdict = "WARN"
        notes.append(tick_msg)

    # 출력
    print(f"[verify_pair_aggregation] {verdict} @ {timezone.now():%Y-%m-%d %H:%M %Z}")
    if not quiet:
        print(f"  PRE: beat={beat_alive} worker={worker_alive}")
        print(f"  A(log): succeeded={succeeded} unregistered={unregistered}")
        print(f"  C(tick): {'OK' if tick_ok else 'ALERT'} — 경계 {tick_boundary:%Y-%m-%d %H:%M %Z}")
        print(f"  B(db): 최신 period={latest}, period 수={len(rows)}")
        for r in rows[-5:]:
            print(f"         {r['period']} → {r['n']}행")
    for n in notes:
        print(f"  ⚠ {n}")
    if verdict == "PASS" and not quiet:
        print("  ✅ 자율 틱 발화·적립 정상 — 궤적 누적 중(본진 학습루프 착수조건 충족).")

    sys.exit({"PASS": 0, "WARN": 1, "FAIL": 2}[verdict])


if __name__ == "__main__":
    main()
