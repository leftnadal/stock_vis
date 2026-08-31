"""DSS 주간 적재 자동화 태스크 (DSS-BEAT-1 §A).

load_dss_weekly: 금요일 19:00 ET — 당일 EstimateSnapshot 발화 확인(가드) 후
store_for_anchor 위임. 서비스 로직 무수정(래핑만). **무재시도**(단순 우선).
멱등: store_for_anchor 사전존재 skip 내장. 명시 beat 등록(#28) = PeriodicTask DB 행(enabled=False→§D enable).
"""
import logging
from zoneinfo import ZoneInfo

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


@shared_task(
    name="chainsight-load-dss-weekly",
    bind=True,
    max_retries=0,  # 무재시도 — DSS-BEAT-1 §A ① (단순 우선·가드 skip은 재시도 아님)
    soft_time_limit=600,
    time_limit=660,
)
def load_dss_weekly(self):
    """주간 DSS 적재. 가드(최신 스냅샷 date ≠ 실행일 ET → skip) → store_for_anchor 위임."""
    from django import db

    db.connections.close_all()  # macOS fork 안전 (Bug #25)

    from apps.chain_sight.models import EstimateSnapshot, ThemeDemandScore
    from apps.chain_sight.services.demand_signal import store_for_anchor

    et_today = timezone.now().astimezone(ET).date()
    latest = (
        EstimateSnapshot.objects.order_by("-snapshot_date")
        .values_list("snapshot_date", flat=True)
        .first()
    )

    # ① 가드: 최신 스냅샷 date ≠ 실행일(ET) → skip (무재시도·단순 우선)
    if latest != et_today:
        logger.warning(
            "load_dss_weekly SKIP: 최신 EstimateSnapshot date=%s ≠ 실행일(ET)=%s "
            "(스냅샷 미발화/비발화일) — 적재 없음",
            latest,
            et_today,
        )
        return {"skipped": True, "latest_snapshot": str(latest), "et_today": str(et_today)}

    # ② store_for_anchor (멱등 skip 내장 — 기존재 anchor 재실행 무해)
    s = store_for_anchor(et_today, dry_run=False)

    # ③ 요약 로그 1줄 (n/up/down/flat/excl · breadth 범위 · flat_ratio)
    n = s["n_signals"]
    denom = n - s["excluded"]
    flat_ratio = s["flat"] / denom if denom else None
    breadths = [
        c.get("breadth")
        for c in ThemeDemandScore.objects.filter(date=et_today).values_list(
            "components", flat=True
        )
        if c and c.get("breadth") is not None
    ]
    br = "[{:.3f},{:.3f}]".format(min(breadths), max(breadths)) if breadths else "n/a"
    logger.info(
        "load_dss_weekly anchor=%s n=%d up=%d down=%d flat=%d excl=%d breadth=%s "
        "flat_ratio=%s written_signals=%d written_scores=%d skipped_existing=%s",
        et_today,
        n,
        s["up"],
        s["down"],
        s["flat"],
        s["excluded"],
        br,
        "{:.2%}".format(flat_ratio) if flat_ratio is not None else "n/a",
        s["written_signals"],
        s["written_scores"],
        s.get("skipped_existing", False),
    )
    return {
        "anchor": str(et_today),
        "n": n,
        "up": s["up"],
        "down": s["down"],
        "flat": s["flat"],
        "excluded": s["excluded"],
        "flat_ratio": flat_ratio,
        "written_signals": s["written_signals"],
        "written_scores": s["written_scores"],
        "skipped_existing": s.get("skipped_existing", False),
    }
