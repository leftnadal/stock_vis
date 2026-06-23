"""
backfill_macro_all (MP-OPS-FRED-ENTRYPOINT, P1-close).

소속: apps/market_pulse/management/commands (운영 백필 단일 진입점).
역할: v2 거시 시계열 전체를 한 커맨드로 날짜범위 백필.
  - backfill_v2_a1 기본 목록(NEW_ECONOMIC_SERIES 11종 + NEW_MARKET_SYMBOLS 11종)
  - + 기본목록 밖 EXTRA_FRED_SERIES(VIXCLS·T10Y2Y) 개별 --series-id 분기 흡수
동기: VIXCLS·T10Y2Y가 backfill_v2_a1 기본목록 밖이라 현재는 진입점이 분기(개별 호출)됨.
구현: **신규 fetch 로직 0** — 기존 backfill_v2_a1을 call_command로 조합만(규약 10장 중복 금지).
      FRED 접근은 backfill_v2_a1 내부의 packages.shared 경유 그대로(shared 무접촉).

사용:
  python manage.py backfill_macro_all --from 2025-06-01 --to 2026-06-23
  python manage.py backfill_macro_all --dry-run
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand

# backfill_v2_a1 기본목록(NEW_ECONOMIC_SERIES) 밖이라 개별 --series-id 분기가 필요한 FRED series.
EXTRA_FRED_SERIES = ("VIXCLS", "T10Y2Y")


class Command(BaseCommand):
    help = (
        "단일 진입점으로 v2 거시 시계열(backfill_v2_a1 기본) + 목록 밖 "
        "FRED(VIXCLS·T10Y2Y)를 날짜범위 백필 (thin wrapper, 신규 fetch 0)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from", dest="from_date", type=str, default=None,
            help="시작일 YYYY-MM-DD (기본: backfill_v2_a1 기본 = to-365d)",
        )
        parser.add_argument(
            "--to", dest="to_date", type=str, default=None,
            help="종료일 YYYY-MM-DD (기본: 오늘)",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="실행 계획만 출력(하위 커맨드에 전파)",
        )

    def handle(self, *args, **options):
        common = {
            "from_date": options["from_date"],
            "to_date": options["to_date"],
            "dry_run": options["dry_run"],
        }
        total = 1 + len(EXTRA_FRED_SERIES)

        # 1) 기본 목록 (econ 11 + market 11) — --series-id/--symbol 미지정 = 전체
        self.stdout.write(f"[backfill_macro_all] 1/{total}: backfill_v2_a1 (기본 목록)")
        call_command("backfill_v2_a1", **common)

        # 2) 기본목록 밖 FRED series 개별 백필 (econ_only=True로 market 중복 재백필 방지)
        for i, series_id in enumerate(EXTRA_FRED_SERIES, start=2):
            self.stdout.write(
                f"[backfill_macro_all] {i}/{total}: backfill_v2_a1 --series-id {series_id} --econ-only"
            )
            call_command("backfill_v2_a1", series_id=series_id, econ_only=True, **common)

        self.stdout.write(
            self.style.SUCCESS(
                f"[backfill_macro_all] 완료 — 기본 목록 + {', '.join(EXTRA_FRED_SERIES)}"
            )
        )
