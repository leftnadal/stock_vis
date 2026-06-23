"""
backfill_v2_a1 — PR-A1 후속 1년치 시계열 백필 management command.

소속: apps/market_pulse/management/commands (app 레이어 운영 커맨드).
역할: 신규 EconomicIndicator 11종 + MarketIndex 11종(XL* GICS sector)의 1년치 시계열
  idempotent 백필. EconomicIndicator는 FRED, MarketIndex는 Yahoo Finance(yfinance).
  동일 명령 재실행 시 추가 적재 행 0.
의존: packages.shared.api_request.fred_client.FREDClient, yfinance, macro.models.

사용:
    python manage.py backfill_v2_a1 --check-pending     # 데이터 0인 신규 series/symbol 탐지
    python manage.py backfill_v2_a1 --dry-run           # 대상 목록만 출력
    python manage.py backfill_v2_a1                     # 전체 백필 (default 365일)
    python manage.py backfill_v2_a1 --series-id NFCI    # 단일 series
    python manage.py backfill_v2_a1 --symbol XLF        # 단일 symbol
    python manage.py backfill_v2_a1 --from 2025-04-01 --to 2026-04-01
    python manage.py backfill_v2_a1 --limit 3           # 대상 수 제한 (테스트)

⚠️ migration 안에서는 호출 금지 (audit P0 #C-Ⅱ). 운영자가 머지 후 수동 실행.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# PR-A1 (2026-04-29): 신규 백필 대상 — migration 0003·0004와 정합
NEW_ECONOMIC_SERIES = (
    'NFCI', 'NFCICREDIT', 'NFCILEVERAGE', 'NFCIRISK',
    'BAMLH0A0HYM2', 'BAMLH0A3HYC',
    'T10Y3M', 'VIX3M', 'MOVE',
    'DGS10', 'DGS2',
)

# XL* GICS sector ETFs (BENCHMARK 9개는 v1에서 이미 적재)
NEW_MARKET_SYMBOLS = (
    'XLF', 'XLK', 'XLV', 'XLY', 'XLP', 'XLE',
    'XLI', 'XLB', 'XLU', 'XLRE', 'XLC',
)


class Command(BaseCommand):
    help = 'Backfill 1-year history for v2 PR-A1 신규 indicators and indices (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--series-id', type=str, default=None,
                            help='특정 series_id만 백필 (생략 시 11개 전체)')
        parser.add_argument('--symbol', type=str, default=None,
                            help='특정 symbol만 백필 (생략 시 신규 11개 전체)')
        parser.add_argument('--from', dest='from_date', type=str, default=None,
                            help='YYYY-MM-DD (기본: 365일 전)')
        parser.add_argument('--to', dest='to_date', type=str, default=None,
                            help='YYYY-MM-DD (기본: 오늘)')
        parser.add_argument('--dry-run', action='store_true',
                            help='실행 없이 대상 목록만 출력')
        parser.add_argument('--check-pending', action='store_true',
                            help='데이터 0인 신규 series/symbol 탐지 후 종료')
        parser.add_argument('--limit', type=int, default=None,
                            help='대상 수 제한 (테스트용)')
        parser.add_argument('--econ-only', action='store_true',
                            help='Economic series만 백필 (Market 심볼 건너뜀). '
                                 'backfill_macro_all가 목록 밖 FRED series 개별 호출 시 '
                                 'market 중복 재백필 방지에 사용')

    def handle(self, *args, **options):
        if options['check_pending']:
            self._check_pending()
            return

        to_date = self._parse_date(options['to_date']) or timezone.now().date()
        from_date = self._parse_date(options['from_date']) or (to_date - timedelta(days=365))

        series_targets = self._resolve_economic_targets(options)
        symbol_targets = self._resolve_market_targets(options)

        if options['dry_run']:
            self.stdout.write(f'[DRY-RUN] {from_date} ~ {to_date}')
            self.stdout.write(f'[DRY-RUN] Economic ({len(series_targets)}): {list(series_targets)}')
            self.stdout.write(f'[DRY-RUN] Market ({len(symbol_targets)}): {list(symbol_targets)}')
            return

        n_econ = 0
        for series_id in series_targets:
            try:
                inserted = self._backfill_economic(series_id, from_date, to_date)
                n_econ += inserted
                self.stdout.write(f'  {series_id}: {inserted} obs inserted')
            except Exception as exc:
                logger.error('Failed to backfill %s: %s', series_id, exc, exc_info=True)
                self.stderr.write(self.style.WARNING(f'  {series_id}: SKIPPED ({exc})'))

        n_market = 0
        for symbol in symbol_targets:
            try:
                inserted = self._backfill_market(symbol, from_date, to_date)
                n_market += inserted
                self.stdout.write(f'  {symbol}: {inserted} bars inserted')
            except Exception as exc:
                logger.error('Failed to backfill %s: %s', symbol, exc, exc_info=True)
                self.stderr.write(self.style.WARNING(f'  {symbol}: SKIPPED ({exc})'))

        self.stdout.write(self.style.SUCCESS(
            f'Backfill complete: {n_econ} econ obs ({len(series_targets)} series), '
            f'{n_market} bars ({len(symbol_targets)} symbols)'
        ))

    # ── helpers ──

    def _parse_date(self, s):
        return datetime.strptime(s, '%Y-%m-%d').date() if s else None

    def _resolve_economic_targets(self, options):
        if options['series_id']:
            return (options['series_id'],)
        targets = NEW_ECONOMIC_SERIES
        if options['limit']:
            targets = targets[:options['limit']]
        return targets

    def _resolve_market_targets(self, options):
        if options.get('econ_only'):
            return ()
        if options['symbol']:
            return (options['symbol'],)
        targets = NEW_MARKET_SYMBOLS
        if options['limit']:
            targets = targets[:options['limit']]
        return targets

    def _check_pending(self):
        from macro.models.indicators import IndicatorValue, MarketIndexPrice
        pending_series = [
            sid for sid in NEW_ECONOMIC_SERIES
            if not IndicatorValue.objects.filter(indicator__code=sid).exists()
        ]
        pending_symbols = [
            sym for sym in NEW_MARKET_SYMBOLS
            if not MarketIndexPrice.objects.filter(index__symbol=sym).exists()
        ]
        self.stdout.write(f'[CHECK] Pending economic ({len(pending_series)}): {pending_series}')
        self.stdout.write(f'[CHECK] Pending market ({len(pending_symbols)}): {pending_symbols}')

    @transaction.atomic
    def _backfill_economic(self, series_id, from_date, to_date):
        """FRED 또는 Yahoo로 series fetch → IndicatorValue idempotent 적재."""
        from macro.models.indicators import EconomicIndicator, IndicatorValue
        indicator = EconomicIndicator.objects.get(code=series_id)

        # VIX3M/MOVE는 FRED 미지원 → Yahoo Finance
        yahoo_map = {'VIX3M': '^VIX3M', 'MOVE': '^MOVE'}
        if series_id in yahoo_map:
            observations = self._fetch_yahoo_indicator(yahoo_map[series_id], from_date, to_date)
        else:
            observations = self._fetch_fred(series_id, from_date, to_date)

        inserted = 0
        for obs in observations:
            try:
                value = Decimal(str(obs['value']))
            except (InvalidOperation, KeyError, TypeError):
                continue
            _, created = IndicatorValue.objects.get_or_create(
                indicator=indicator,
                date=obs['date'],
                defaults={'value': value},
            )
            if created:
                inserted += 1
        return inserted

    @transaction.atomic
    def _backfill_market(self, symbol, from_date, to_date):
        """Yahoo Finance로 OHLCV fetch → MarketIndexPrice idempotent 적재."""
        from macro.models.indicators import MarketIndex, MarketIndexPrice
        index = MarketIndex.objects.get(symbol=symbol)
        bars = self._fetch_yahoo_ohlc(symbol, from_date, to_date)
        inserted = 0
        for bar in bars:
            _, created = MarketIndexPrice.objects.get_or_create(
                index=index,
                date=bar['date'],
                defaults={
                    'open': bar.get('open'),
                    'high': bar.get('high'),
                    'low': bar.get('low'),
                    'close': bar['close'],
                    'volume': bar.get('volume'),
                },
            )
            if created:
                inserted += 1
        return inserted

    def _fetch_fred(self, series_id, from_date, to_date):
        from packages.shared.api_request.fred_client import FREDClient
        client = FREDClient()
        raw = client.get_series_observations(series_id, observation_start=str(from_date), observation_end=str(to_date))
        out = []
        for r in raw:
            d_str = r.get('date')
            v_str = r.get('value')
            if not d_str or not v_str or v_str == '.':
                continue
            out.append({'date': datetime.strptime(d_str, '%Y-%m-%d').date(), 'value': v_str})
        return out

    def _fetch_yahoo_indicator(self, ticker, from_date, to_date):
        import yfinance as yf
        df = yf.Ticker(ticker).history(start=str(from_date), end=str(to_date))
        out = []
        for ts, row in df.iterrows():
            close = row.get('Close')
            if close is None or (close != close):  # NaN check
                continue
            out.append({'date': ts.date(), 'value': float(close)})
        return out

    def _fetch_yahoo_ohlc(self, symbol, from_date, to_date):
        import yfinance as yf
        df = yf.Ticker(symbol).history(start=str(from_date), end=str(to_date))
        out = []
        for ts, row in df.iterrows():
            close = row.get('Close')
            if close is None or (close != close):
                continue
            out.append({
                'date': ts.date(),
                'open': float(row['Open']) if row.get('Open') == row.get('Open') else None,
                'high': float(row['High']) if row.get('High') == row.get('High') else None,
                'low': float(row['Low']) if row.get('Low') == row.get('Low') else None,
                'close': float(close),
                'volume': int(row['Volume']) if row.get('Volume') == row.get('Volume') else None,
            })
        return out
