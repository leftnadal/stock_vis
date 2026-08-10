"""
P2a-1c: EtfNavHistory 혼합행 C″ 재귀속 (management command, dry-run 기본).

C′ 시절 저장된 행은 quote 정본거래일(T)에 nav(=T-1 종가)를 묶은 혼합이다. 각 행을
nav_updated_at 기반 D-1 거래일로 재귀속하고 price를 EOD 이력의 D-1 종가로 교체한다.
삭제 없음(§10): 재귀속은 date 필드 UPDATE(이동)로만. 신설 행(예: 08-04)은 --nav-json
으로 nav를 주입(하드코딩 아님)하고 price는 EOD 이력에서 페어링.

★ 실행은 배포 승인 후. --dry-run이 기본, 실제 반영은 --execute 명시 시에만.

사용:
    python manage.py reattribute_etf_nav                       # dry-run (계획만)
    python manage.py reattribute_etf_nav --nav-json seed.json  # dry-run + 신설 계획
    python manage.py reattribute_etf_nav --execute --nav-json seed.json   # 실제 반영

--nav-json 형식: {"2026-08-04": {"HYG": "79.40", "LQD": "106.69"}}
"""
import json
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

_ET = ZoneInfo("America/New_York")


class Command(BaseCommand):
    help = (
        "P2a-1c EtfNavHistory 혼합행 C″ 재귀속(D-1) + price EOD 교체 + 신설행 주입. "
        "dry-run 기본, --execute 시에만 DB 반영."
    )

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true", help="실제 DB 반영(기본=dry-run)")
        parser.add_argument("--nav-json", type=str, default=None,
                            help="신설 행 nav 주입 JSON {date:{symbol:nav}}")

    def handle(self, *args, **options):
        import os

        from packages.shared.api_request.providers.fmp.client import FMPClient
        from ...models import EtfNavHistory
        from ...services.etf_nav_service import _eod_close
        from ...trading_calendar import previous_trading_day

        execute = options["execute"]
        mode = "EXECUTE" if execute else "DRY-RUN"
        client = FMPClient(api_key=os.getenv("FMP_API_KEY"))
        self.stdout.write(f"=== reattribute_etf_nav [{mode}] ===")

        moved = held = ok = 0

        # ── 1. 기존 행 재귀속 (nav_updated_at 기반 D-1) ──
        for row in EtfNavHistory.objects.all().order_by("symbol", "date"):
            if row.nav_updated_at is None:
                held += 1
                self.stdout.write(f"  HOLD {row.symbol}@{row.date}: nav_updated_at 없음 — 재귀속 근거 불가(보고만)")
                continue
            pub_date = row.nav_updated_at.astimezone(_ET).date()
            new_td = previous_trading_day(pub_date)
            if new_td == row.date:
                ok += 1
                continue  # 이미 정합
            new_price = _eod_close(client, row.symbol, new_td)
            if new_price is None:
                held += 1
                self.stdout.write(f"  HOLD {row.symbol}@{row.date}→{new_td}: EOD 종가 미확보 — 검증 불가(보고만)")
                continue
            conflict = (
                EtfNavHistory.objects.filter(symbol=row.symbol, date=new_td)
                .exclude(pk=row.pk).exists()
            )
            if conflict:
                held += 1
                self.stdout.write(f"  HOLD {row.symbol}@{row.date}→{new_td}: 대상 거래일 행 이미 존재 — 충돌(보고만)")
                continue
            moved += 1
            self.stdout.write(
                f"  MOVE {row.symbol}: {row.date}→{new_td} | price {row.price}→{new_price} | nav {row.nav} 유지"
            )
            if execute:
                row.date = new_td
                row.price = new_price
                row.revised_at = timezone.now()
                row.save(update_fields=["date", "price", "revised_at"])

        # ── 2. 신설 행 (--nav-json) ──
        created = 0
        if options["nav_json"]:
            with open(options["nav_json"]) as f:
                seed = json.load(f)
            for dstr, syms in seed.items():
                td = date.fromisoformat(dstr)
                for sym, navval in syms.items():
                    if EtfNavHistory.objects.filter(symbol=sym, date=td).exists():
                        self.stdout.write(f"  SKIP {sym}@{td}: 이미 존재")
                        continue
                    price = _eod_close(client, sym, td)
                    if price is None:
                        held += 1
                        self.stdout.write(f"  HOLD {sym}@{td}(신설): EOD 종가 미확보(보고만)")
                        continue
                    created += 1
                    self.stdout.write(f"  CREATE {sym}@{td}: nav={navval} price={price} (nav_updated_at=null, 소급주입)")
                    if execute:
                        EtfNavHistory.objects.create(
                            symbol=sym, date=td, nav=Decimal(str(navval)), price=price,
                        )

        self.stdout.write(self.style.SUCCESS(
            f"[{mode}] 완료: move={moved} create={created} hold={held} already_ok={ok}"
        ))
        if not execute:
            self.stdout.write(self.style.WARNING("dry-run — DB 무변경. 실제 반영은 --execute."))
