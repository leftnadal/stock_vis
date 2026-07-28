"""backfill_spy_eod — A-PREP: SPY EOD 3년 재백필 (shared FMP 래퍼, 멱등, dry-run 기본).

소속: apps/market_pulse/management/commands (backfill_v2_a1 선례 재사용 — B-1 축소판).
역할: 롤링 purge(cleanup_old_data)에 잘려나간 SPY EOD 과거 구간을 shared FMP 래퍼로
  재백필해 analog 사후수익률 모집단(683)을 회복한다. macro.MarketIndexPrice에 idempotent
  upsert. 재백필 자산은 A-S0(PRESERVED_INDEX_SYMBOLS)로 이후 purge에서 제외된다.
의존: packages.shared.api_request.providers.fmp.client.FMPClient (shared 래퍼, /stable/*),
  macro.models(MarketIndex·MarketIndexPrice).

규약:
  - **dry-run 기본**: 인자 없이 실행 = 무쓰기 산정 리포트. 실제 쓰기는 `--commit` 명시.
  - 멱등: 존재 (index,date) 행 skip(get_or_create) — 재실행 추가 0.
  - 외부는 shared FMP 래퍼 경유만(직접 호출 0).

사용:
    python manage.py backfill_spy_eod                 # dry-run(기본): 채울 행수·범위·출처
    python manage.py backfill_spy_eod --from 2023-07-14 --to 2026-07-13
    python manage.py backfill_spy_eod --commit        # 실제 쓰기(운영자 승인 후)

⚠️ prod 쓰기 = 운영자 수동(--commit). 개발 중 실 API는 최소.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DEFAULT_SYMBOL = "SPY"
DEFAULT_YEARS = 3


class Command(BaseCommand):
    help = "Backfill SPY EOD via shared FMP wrapper (idempotent, dry-run 기본)."

    def add_arguments(self, parser):
        parser.add_argument("--symbol", type=str, default=DEFAULT_SYMBOL)
        parser.add_argument(
            "--from", dest="from_date", type=str, default=None,
            help="YYYY-MM-DD (기본: 오늘-3년)",
        )
        parser.add_argument(
            "--to", dest="to_date", type=str, default=None,
            help="YYYY-MM-DD (기본: 오늘)",
        )
        parser.add_argument(
            "--commit", action="store_true",
            help="실제 DB 쓰기(미지정 시 dry-run 리포트만)",
        )

    def handle(self, *args, **options):
        from macro.models.indicators import MarketIndex, MarketIndexPrice

        symbol = options["symbol"].upper()
        to_date = self._parse(options["to_date"]) or date.today()
        from_date = self._parse(options["from_date"]) or (
            date.today() - timedelta(days=365 * DEFAULT_YEARS)
        )
        if to_date < from_date:
            raise CommandError(f"빈 창: from={from_date} > to={to_date}")

        index = MarketIndex.objects.filter(symbol=symbol).first()
        if index is None:
            raise CommandError(f"MarketIndex({symbol}) 없음 — 먼저 등록 필요.")

        existing = set(
            MarketIndexPrice.objects.filter(
                index=index, date__gte=from_date, date__lte=to_date
            ).values_list("date", flat=True)
        )

        rows = self._fetch(symbol, from_date, to_date)
        parsed = [r for r in (self._normalize(r) for r in rows) if r is not None]
        in_window = [r for r in parsed if from_date <= r["date"] <= to_date]
        to_insert = [r for r in in_window if r["date"] not in existing]

        dates = [r["date"] for r in to_insert]
        self.stdout.write(
            f"[{'COMMIT' if options['commit'] else 'DRY-RUN'}] symbol={symbol} "
            f"창={from_date}~{to_date}"
        )
        self.stdout.write(
            f"  FMP 반환 {len(parsed)}행 / 창내 {len(in_window)} / "
            f"기존 {len(in_window) - len(to_insert)} skip / 신규 삽입대상 {len(to_insert)}"
        )
        if dates:
            self.stdout.write(f"  삽입 날짜 범위: {min(dates)} ~ {max(dates)}")
        self.stdout.write("  출처: FMP /stable/historical-price-eod/full (shared 래퍼)")

        if not options["commit"]:
            self.stdout.write(
                self.style.WARNING("  DRY-RUN — 쓰기 없음. 실제 실행은 --commit.")
            )
            return

        inserted = 0
        for r in to_insert:
            _, created = MarketIndexPrice.objects.get_or_create(
                index=index, date=r["date"], defaults=r["defaults"]
            )
            if created:
                inserted += 1
        self.stdout.write(
            self.style.SUCCESS(f"  삽입 완료: {inserted} 신규 / {len(to_insert) - inserted} 경합skip")
        )

    # ── helpers ──

    def _parse(self, s):
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None

    def _fetch(self, symbol, from_date, to_date):
        """shared FMP 래퍼 경유 EOD 조회(직접 호출 0)."""
        from packages.shared.api_request.providers.fmp.client import FMPClient

        key = getattr(settings, "FMP_API_KEY", None) or os.environ.get("FMP_API_KEY")
        if not key:
            raise CommandError("FMP_API_KEY 없음 — shared 래퍼 인증 불가.")
        client = FMPClient(api_key=key)
        return client.get_historical_price(
            symbol, from_date=str(from_date), to_date=str(to_date)
        ) or []

    def _normalize(self, r):
        """FMP EOD dict → {date, defaults}. 파싱 실패 행은 None(건너뜀)."""
        d = r.get("date")
        close = r.get("close")
        if not d or close is None:
            return None
        try:
            dd = datetime.strptime(d[:10], "%Y-%m-%d").date()
            defaults = {
                "open": self._dec(r.get("open")),
                "high": self._dec(r.get("high")),
                "low": self._dec(r.get("low")),
                "close": Decimal(str(close)),
                "volume": int(r["volume"]) if r.get("volume") is not None else None,
                "change": self._dec(r.get("change")),
                "change_percent": self._dec(r.get("changePercent")),
            }
        except (InvalidOperation, ValueError, TypeError):
            return None
        return {"date": dd, "defaults": defaults}

    def _dec(self, v):
        if v is None:
            return None
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError):
            return None
