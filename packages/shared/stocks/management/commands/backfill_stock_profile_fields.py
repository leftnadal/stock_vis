"""R1 Phase A/B — Stock sector/industry/market_cap 백필 (shared FMP 래퍼 경유).

CS-SECTOR-BACKFILL(sector/industry) + CS-P4-MC-BACKFILL(market_cap) 공용.
shared StockService.get_company_profile(=call_with_fallback·circuit breaker 내장)만 사용.
개별 종목 skip은 목록화(HALT 아님), 전체 응답 이상 시 사용자가 HALT 판단.

사용:
  --list-file <path>   백필 대상 심볼(줄바꿈 구분) 스냅샷
  --fields sector,industry,market_cap   채울 필드(결측인 것만 갱신)
  --dry-run            FMP/DB 무접촉, 계획만
  --limit N            앞 N개만(preprobe용)
"""
import time

from django.core.management.base import BaseCommand

from packages.shared.api_request.stock_service import StockService
from packages.shared.stocks.models import Stock


class Command(BaseCommand):
    help = "Stock 프로필 필드(sector/industry/market_cap) FMP 백필 (결측만 갱신·shared 래퍼)."

    def add_arguments(self, parser):
        parser.add_argument("--list-file", required=True)
        parser.add_argument("--fields", default="sector,industry")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **o):
        fields = [f.strip() for f in o["fields"].split(",") if f.strip()]
        with open(o["list-file"] if False else o["list_file"]) as fh:
            symbols = [ln.strip().upper() for ln in fh if ln.strip()]
        if o["limit"]:
            symbols = symbols[: o["limit"]]

        self.stdout.write(f"대상 {len(symbols)}종목 · 채울 필드={fields} · dry_run={o['dry_run']}")
        self.stdout.write(f"[accounting] 예상 FMP 콜(1콜/종목) = {len(symbols)}")
        if o["dry_run"]:
            self.stdout.write("dry-run: FMP/DB 무접촉 종료 · 대상 앞10=" + ",".join(symbols[:10]))
            return

        svc = StockService()
        calls = 0
        updated, skipped = [], {}
        # 필드→프로필 속성 매핑
        attr = {"sector": "sector", "industry": "industry", "market_cap": "market_cap"}
        col = {"sector": "sector", "industry": "industry", "market_cap": "market_capitalization"}
        for sym in symbols:
            try:
                resp = svc.get_company_profile(sym)
                calls += 1
            except Exception as e:  # noqa: BLE001
                skipped[sym] = f"exception:{repr(e)[:50]}"
                continue
            if not getattr(resp, "success", False) or resp.data is None:
                skipped[sym] = f"profile_fail:{getattr(resp, 'error', 'no_coverage')}"
                continue
            p = resp.data
            try:
                st = Stock.objects.get(symbol=sym)
            except Stock.DoesNotExist:
                skipped[sym] = "stock_missing"
                continue
            changed = []
            for f in fields:
                val = getattr(p, attr[f], None)
                cur = getattr(st, col[f], None)
                empty = cur in (None, "", 0)
                if val not in (None, "", 0) and empty:
                    setattr(st, col[f], val)
                    changed.append(f"{f}={val}")
            if changed:
                st.save(update_fields=[col[f] for f in fields if any(c.startswith(f + "=") for c in changed)])
                updated.append((sym, changed))
            else:
                skipped[sym] = "no_new_field(응답에 값 없음 or 이미 채워짐)"
            time.sleep(0.22)  # FMP Starter 300/min 여유

        self.stdout.write(self.style.SUCCESS(f"[accounting] 실제 FMP 콜 = {calls}"))
        self.stdout.write(f"갱신 {len(updated)} · skip {len(skipped)}")
        for sym, ch in updated[:20]:
            self.stdout.write(f"  ✓ {sym}: {ch}")
        if skipped:
            self.stdout.write(self.style.WARNING(f"skip 목록({len(skipped)}):"))
            for sym, why in list(skipped.items())[:40]:
                self.stdout.write(f"  ✗ {sym}: {why}")
