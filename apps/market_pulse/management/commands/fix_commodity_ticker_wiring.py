"""fix_commodity_ticker_wiring — A-3(HUB-V02-S1): 티커 스트립 금·은 배선 교정.

배경(HUB-V02-RECON Part E): 홈 TickerBar는 `MarketIndex.sector_group ∈ (BENCHMARK+GICS)`만 노출.
  GCUSD/SIUSD(금·은 현물)는 오늘자 가격이 있으나 sector_group=None이라 스트립에서 제외되고,
  GLD/SLV(ETF)는 BENCHMARK지만 price 0행이라 "—"로 표시됨(402 아님, 배선 불일치).
교정: GCUSD/SIUSD None→BENCHMARK(실데이터 노출). GLD/SLV(빈 심볼)는 별도 데이터 쓰기 없이
  `_ticker_bar` 코드가 null-price 행을 스킵(A-3 코드 반영)하므로 여기서 sector_group 쓰기 불요.
  (sector_group은 모델상 non-null·default BENCHMARK — None 쓰기 회피, prod 스키마 drift 비의존.)
멱등: 이미 BENCHMARK면 스킵. dry-run 기본. `--commit`로 집행.
  ⚠ prod DB 쓰기 — 병진 승인 후 집행(HUB-V02-S1 §2).
"""

from django.core.management.base import BaseCommand

from macro.models.indicators import MarketIndex, MarketIndexPrice

ADD_TO_BENCHMARK = ["GCUSD", "SIUSD"]  # None → BENCHMARK (실데이터 노출)
EMPTY_ETF = ["GLD", "SLV"]  # 0행 — 코드가 null-price 스킵(정보 표기만)
BENCHMARK = "BENCHMARK"


class Command(BaseCommand):
    help = "티커 스트립 금·은 배선 교정 (idempotent, dry-run 기본)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit", action="store_true", help="실제 sector_group 쓰기(미지정=dry-run)"
        )

    def _row(self, sym):
        mi = MarketIndex.objects.filter(symbol=sym).first()
        rows = MarketIndexPrice.objects.filter(index=mi).count() if mi else 0
        return mi, rows

    def handle(self, *args, **opts):
        commit = opts["commit"]
        self.stdout.write(f"[fix_commodity_ticker_wiring] commit={commit}")
        changed = 0

        for sym in ADD_TO_BENCHMARK:
            mi, rows = self._row(sym)
            cur = repr(mi.sector_group) if mi else "(MarketIndex 부재)"
            self.stdout.write(f"  {sym}: sector_group {cur} → 'BENCHMARK'  (price행={rows})")
            if commit and mi and mi.sector_group != BENCHMARK:
                mi.sector_group = BENCHMARK
                mi.save(update_fields=["sector_group"])
                changed += 1

        for sym in EMPTY_ETF:
            mi, rows = self._row(sym)
            cur = repr(mi.sector_group) if mi else "(MarketIndex 부재)"
            self.stdout.write(
                f"  {sym}: sector_group {cur} · price행={rows} → 쓰기 없음(코드가 null-price 스킵)"
            )

        if not commit:
            self.stdout.write("  DRY-RUN: 쓰기 없음. --commit 로 교정 집행.")
        else:
            self.stdout.write(self.style.SUCCESS(f"  교정 {changed}건 적용(GCUSD/SIUSD)."))
