"""
C2b 발행 신호 수집 (TH-3) — 424B5 일 단위 창 순회 + IPO 캘린더 범위.

설계서 theme_heat_design.md v1.2.1 §5.2. 본문 파싱 아님(폼타입·날짜·심볼 카운팅).

실행 원칙: **전경 블로킹**(백그라운드 금지). 장기 백필은 경계 배치(--from/--to)로 잘라
순차 전경 실행 + 멱등 upsert 로 재개 안전.

사용:
    python manage.py collect_theme_filings --days 14              # 최근 14일 424B5+IPO
    python manage.py collect_theme_filings --from 2026-04-01 --to 2026-07-06
    python manage.py collect_theme_filings --days 30 --no-ipo     # 424B5 만
    python manage.py collect_theme_filings --days 3 --dry-run     # 무적재 형상 확인
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.chain_sight.services.filing_service import (
    FORM_424B5,
    collect_424b5_for_day,
    collect_424b5_range,
    collect_ipos_range,
)
from packages.shared.api_request.providers.fmp.client import FMPClient


class Command(BaseCommand):
    help = "FMP 424B5(일창 순회) + IPO 캘린더 수집 → ThemeFilingCount (멱등, 전경)."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="from_date", type=str, help="시작일 YYYY-MM-DD")
        parser.add_argument("--to", dest="to_date", type=str, help="종료일 YYYY-MM-DD(기본 오늘)")
        parser.add_argument("--days", type=int, default=None, help="최근 N일(--from 대체)")
        parser.add_argument("--no-ipo", action="store_true", help="424B5 만 수집")
        parser.add_argument("--dry-run", action="store_true", help="무적재 — 하루 형상만")

    def handle(self, *args, **opts):
        from datetime import date as date_type

        today = timezone.now().date()
        to_date = date_type.fromisoformat(opts["to_date"]) if opts["to_date"] else today
        if opts["days"] is not None:
            from_date = to_date - timedelta(days=opts["days"] - 1)
        elif opts["from_date"]:
            from_date = date_type.fromisoformat(opts["from_date"])
        else:
            raise CommandError("--from 또는 --days 중 하나는 필수")
        if from_date > to_date:
            raise CommandError(f"from({from_date}) > to({to_date})")

        client = FMPClient(api_key=settings.FMP_API_KEY)
        self.stdout.write(
            f"424B5 수집 {from_date} ~ {to_date} ({(to_date - from_date).days + 1}일) · "
            f"IPO {'제외' if opts['no_ipo'] else '포함'} · "
            f"{'DRY-RUN' if opts['dry_run'] else '실적재'}"
        )

        if opts["dry_run"]:
            rows = client.get_sec_filings_by_form_type(
                FORM_424B5, to_date.isoformat(), to_date.isoformat()
            )
            exact = [r for r in rows if r.get("formType") == FORM_424B5]
            with_sym = [r for r in exact if r.get("symbol")]
            self.stdout.write(
                f"  {to_date} 424B5: fetched={len(rows)} exact={len(exact)} "
                f"with_symbol={len(with_sym)} (무적재)"
            )
            return

        agg = collect_424b5_range(client, from_date, to_date, log_fn=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(
            f"424B5: days={agg['days']} fetched={agg['fetched']} exact={agg['exact']} "
            f"created={agg['created']} skip_form={agg['skipped_form']} "
            f"skip_no_symbol={agg['skipped_no_symbol']}"
        ))

        if not opts["no_ipo"]:
            ipo = collect_ipos_range(client, from_date, to_date)
            self.stdout.write(self.style.SUCCESS(
                f"IPO: fetched={ipo['fetched']} created={ipo['created']} "
                f"skip_exchange={ipo['skipped_exchange']} skip_no_symbol={ipo['skipped_no_symbol']}"
            ))
