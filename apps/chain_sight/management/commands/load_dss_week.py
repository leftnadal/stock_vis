"""DSS 주간 적재 폴백/백필 command (DSS-BEAT-1 §A).

`manage.py load_dss_week [--anchor YYYY-MM-DD]` — store_for_anchor 위임 + invariant·
flat_ratio 판정(§2 기계 기준)·arrow 상태 출력. 기본 anchor = 최신 EstimateSnapshot 일자.
서비스 로직 무수정(래핑). 멱등: 기존재 anchor 재실행 무해(store 사전존재 skip).
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.chain_sight.models import (
    EstimateSnapshot,
    SymbolDemandSignal,
    ThemeDemandScore,
)
from apps.chain_sight.services.demand_signal import store_for_anchor
from apps.chain_sight.services.sector_quadrant import (
    SUPPRESS_FLAT_RATIO,
    build_quadrant,
)


class Command(BaseCommand):
    help = "DSS 주간 적재(폴백/백필). 기본 anchor = 최신 EstimateSnapshot 일자."

    def add_arguments(self, parser):
        parser.add_argument(
            "--anchor", type=str, default=None, help="YYYY-MM-DD (기본=최신 스냅샷)"
        )

    def handle(self, *args, **opts):
        if opts["anchor"]:
            try:
                anchor = date.fromisoformat(opts["anchor"])
            except ValueError as e:
                raise CommandError(f"--anchor 형식 오류(YYYY-MM-DD): {e}")
        else:
            anchor = (
                EstimateSnapshot.objects.order_by("-snapshot_date")
                .values_list("snapshot_date", flat=True)
                .first()
            )
        if anchor is None:
            raise CommandError("EstimateSnapshot 없음 — 적재 불가")

        s = store_for_anchor(anchor, dry_run=False)

        # invariant (date-scoped, DSS-IMPL-1 Slice 4)
        sigs = list(
            SymbolDemandSignal.objects.filter(anchor_date=anchor).values_list(
                "direction", "excluded"
            )
        )
        n = len(sigs)
        up = sum(1 for d, e in sigs if not e and d == 1)
        down = sum(1 for d, e in sigs if not e and d == -1)
        flat = sum(1 for d, e in sigs if not e and d == 0)
        excl = sum(1 for d, e in sigs if e)
        scores = list(
            ThemeDemandScore.objects.filter(date=anchor).values_list(
                "status", "components"
            )
        )
        breadths = [c.get("breadth") for _, c in scores if c.get("breadth") is not None]
        denoms = [
            c.get("valid_denom") for st, c in scores if st != "not_computed"
        ]
        inv1 = up + down + flat + excl == n
        inv2 = all(-1 <= b <= 1 for b in breadths)
        inv3 = all(d > 0 for d in denoms)

        self.stdout.write(
            f"anchor={anchor} written_signals={s['written_signals']} "
            f"written_scores={s['written_scores']} "
            f"skipped_existing={s.get('skipped_existing', False)}"
        )
        self.stdout.write(f"  n={n} up={up} down={down} flat={flat} excl={excl}")
        self.stdout.write(
            f"  invariant: 합=n {inv1} · breadth∈[-1,1] {inv2} · 유효분모>0 {inv3} · Score={len(scores)}"
        )
        denom = n - excl
        if denom:
            fr = flat / denom * 100
            verdict = "정상 <60" if fr < 60 else ("재발 ≥90" if fr >= 90 else "회색 60~90")
            self.stdout.write(f"  flat_ratio={fr:.2f}% ({verdict})")
        else:
            self.stdout.write("  flat_ratio=n/a (유효분모 0)")

        # arrow (최신 2 anchor 기준 — build_quadrant)
        q = build_quadrant()
        self.stdout.write(
            f"  arrow_suppressed={q['arrow_suppressed']} "
            f"(curr={q['flat_ratio_curr']} prev={q['flat_ratio_prev']} 임계={SUPPRESS_FLAT_RATIO})"
        )
