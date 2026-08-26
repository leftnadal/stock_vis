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

# P2a-1f cutover 경계 — FMP nav 게시 로테이션 fix go-live.
# 출처: 공급자 서면 확인(08-24 티켓 회신 = FMP fix go-live 08-14) + iShares 교차검증
# 실측(pub 08-13분까지=오전 파싱 T-1 정합 / 08-14분부터=저녁 스윕 T-0 당일).
# pub_date >= 이 경계 = post-fix(T-0 당일 귀속), 미만 = pre-fix(T-1 전일, 역사 보존).
# ※ 이 경계는 "과거 원장을 다루는 재귀속 도구" 전용. 신규 수집 resolve(P2a-1e)는
#   post-fix만 다루므로 cutover 불요(무접촉).
FMP_T0_CUTOVER_ET = date(2026, 8, 14)


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
        from ...trading_calendar import is_trading_day, previous_trading_day

        execute = options["execute"]
        mode = "EXECUTE" if execute else "DRY-RUN"
        client = FMPClient(api_key=os.getenv("FMP_API_KEY"))
        self.stdout.write(f"=== reattribute_etf_nav [{mode}] ===")

        moved = held = ok = 0

        # ── 1. 기존 행 재귀속 (cutover 경계 T-1/T-0) ──
        # Pass 1: 이동 후보 산출. 역순(source date 내림차순)으로 순회해 cascade(연쇄
        # 이동, 예: 08-13→08-14→08-17→08-18) 시 목적지가 먼저 비워지도록 한다.
        candidates = []  # [(row, new_td, new_price)]
        for row in EtfNavHistory.objects.all().order_by("symbol", "-date"):
            if row.nav_updated_at is None:
                held += 1
                self.stdout.write(f"  HOLD {row.symbol}@{row.date}: nav_updated_at 없음 — 재귀속 근거 불가(보고만)")
                continue
            pub_date = row.nav_updated_at.astimezone(_ET).date()
            # cutover 경계: post-fix=T-0 당일(비거래일 pub은 무이동), pre-fix=T-1 전일.
            if pub_date >= FMP_T0_CUTOVER_ET:
                if not is_trading_day(pub_date):
                    held += 1
                    self.stdout.write(f"  HOLD {row.symbol}@{row.date}: post-fix 비거래일 pub={pub_date} — 이동 대상 아님(보고만)")
                    continue
                new_td = pub_date
            else:
                new_td = previous_trading_day(pub_date)
            if new_td == row.date:
                ok += 1
                continue  # 이미 정합
            new_price = _eod_close(client, row.symbol, new_td)
            if new_price is None:
                held += 1
                self.stdout.write(f"  HOLD {row.symbol}@{row.date}→{new_td}: EOD 종가 미확보 — 검증 불가(보고만)")
                continue
            candidates.append((row, new_td, new_price))

        # 이동으로 비워질 (symbol, date) 집합 — cascade 목적지 충돌 오판 방지.
        vacating = {(r.symbol, r.date) for r, _, _ in candidates}

        # Pass 2: 충돌 판정(vacating 인지) + 이동. 역순 유지 = execute 시 목적지 선비움.
        for row, new_td, new_price in candidates:
            occupant = (
                EtfNavHistory.objects.filter(symbol=row.symbol, date=new_td)
                .exclude(pk=row.pk).exists()
            )
            # 목적지가 스스로 이동하는 행이면(vacating) 충돌 아님 — cascade 정상.
            if occupant and (row.symbol, new_td) not in vacating:
                held += 1
                self.stdout.write(f"  HOLD {row.symbol}@{row.date}→{new_td}: 대상 거래일 행 이미 존재(비이동) — 충돌(보고만)")
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
