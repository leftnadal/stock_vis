"""recompute_breadth_history — A-1(HUB-V02-S1): 과거 BreadthSnapshot 소급 재계산.

배경: 종전 `compute_breadth`가 오늘(localdate) 기준으로 EOD DailyPrice를 조회해 항상 total=0.
  코드 수리(직전 거래일 해석) 후에도 과거 스냅샷(0행)은 그대로 남으므로 이 커맨드로 소급 재계산.
멱등: `compute_breadth`는 순수 재계산, `upsert_snapshot`은 update_or_create. 재실행 안전.
dry-run 기본(무쓰기 산정 리포트). 실제 쓰기는 `--commit`. 비거래일 0-스냅샷 정리는 `--purge-bogus`.
  ⚠ prod DB 쓰기 — 병진 승인 후 집행(HUB-V02-S1 §2).
"""

from django.core.management.base import BaseCommand

from apps.market_pulse.calculators.breadth import (
    _resolve_universe_symbols,
    compute_breadth,
    upsert_snapshot,
)
from apps.market_pulse.models.snapshot import BreadthSnapshot
from packages.shared.stocks.models import DailyPrice


class Command(BaseCommand):
    help = "Breadth 과거 스냅샷 소급 재계산 (idempotent, dry-run 기본)."

    def add_arguments(self, parser):
        parser.add_argument("--universe", type=str, default="SPY")
        parser.add_argument(
            "--commit", action="store_true", help="실제 재계산·쓰기(미지정=dry-run)"
        )
        parser.add_argument(
            "--purge-bogus",
            action="store_true",
            help="비거래일(DailyPrice 없는 날) 스냅샷 삭제(--commit 동반 시만)",
        )

    def handle(self, *args, **opts):
        universe = opts["universe"]
        commit = opts["commit"]
        purge = opts["purge_bogus"]

        symbols = _resolve_universe_symbols(universe)
        dates = list(
            DailyPrice.objects.filter(stock_id__in=symbols)
            .values_list("date", flat=True)
            .distinct()
            .order_by("date")
        )
        trade_dates = set(dates)
        existing = BreadthSnapshot.objects.filter(universe=universe)
        total_rows = existing.count()
        zero_rows = existing.filter(total_count=0).count()
        bogus = [s.date for s in existing if s.date not in trade_dates]

        self.stdout.write(f"[recompute_breadth_history] universe={universe} commit={commit}")
        self.stdout.write(
            f"  거래일(DailyPrice distinct): {len(dates)}"
            + (f"  범위 {dates[0]}~{dates[-1]}" if dates else "  (거래일 0)")
        )
        self.stdout.write(
            f"  기존 BreadthSnapshot: {total_rows}행 (total=0: {zero_rows})"
        )
        self.stdout.write(f"  비거래일 스냅샷(purge 후보): {len(bogus)}")

        if not commit:
            self.stdout.write("  DRY-RUN: 쓰기 없음. --commit 로 재계산 집행.")
            return

        # 크로놀로지컬 재계산 — AD-line 연속성(각 일자가 직전 스냅샷 ad_line 위에 누적).
        recomputed = 0
        for d in dates:
            metrics = compute_breadth(universe=universe, target_date=d)
            upsert_snapshot(metrics, universe=universe, target_date=d)
            recomputed += 1
        purged = 0
        if purge:
            for d in bogus:
                purged += BreadthSnapshot.objects.filter(
                    universe=universe, date=d
                ).delete()[0]
        self.stdout.write(
            self.style.SUCCESS(f"  재계산 {recomputed}일 완료. purge {purged}행.")
        )
