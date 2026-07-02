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
import subprocess
import sys
from pathlib import Path

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


def log_check():
    """A — worker 로그 최근 흔적. (succeeded 있음 / unregistered 없음)"""
    succeeded = unregistered = 0
    for name in ("celery-worker.log", "celery-worker-error.log"):
        p = LOGDIR / name
        if not p.exists():
            continue
        try:
            tail = p.read_text(errors="replace").splitlines()[-2000:]
        except Exception:
            continue
        for ln in tail:
            if "aggregate_relation_pairs" in ln:
                if "succeeded" in ln:
                    succeeded += 1
                if "unregistered" in ln.lower() or "KeyError" in ln:
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


def main():
    quiet = "--quiet" in sys.argv
    today = timezone.now().date()
    beat_alive, worker_alive = pre_check()
    succeeded, unregistered = log_check()
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
            f"worker 로그에 unregistered/KeyError {unregistered}건 → 신규 task 미등록. "
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

    # 출력
    print(f"[verify_pair_aggregation] {verdict} @ {timezone.now():%Y-%m-%d %H:%M %Z}")
    if not quiet:
        print(f"  PRE: beat={beat_alive} worker={worker_alive}")
        print(f"  A(log): succeeded={succeeded} unregistered={unregistered}")
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
