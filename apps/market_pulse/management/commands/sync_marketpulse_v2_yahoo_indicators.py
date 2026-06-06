"""
sync_marketpulse_v2_yahoo_indicators — yfinance VIX3M/MOVE 시계열 동기화.

소속: apps/market_pulse/management/commands (app 레이어 운영 커맨드).
역할: FRED 미지원 보완 — CBOE VIX3M(`^VIX3M`)과 ICE BofAML MOVE(`^MOVE`)를 yfinance로
  일별 종가 fetch → EconomicIndicator(VIX3M/MOVE) + IndicatorValue 저장.
의존: yfinance, macro.models.

사용:
    python manage.py sync_marketpulse_v2_yahoo_indicators
    python manage.py sync_marketpulse_v2_yahoo_indicators --period 1y
    python manage.py sync_marketpulse_v2_yahoo_indicators --series VIX3M --period 6mo
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# EconomicIndicator.code → Yahoo Finance ticker
SERIES_MAP = {
    'VIX3M': '^VIX3M',
    'MOVE': '^MOVE',
}


class Command(BaseCommand):
    help = 'Yahoo Finance로 VIX3M / MOVE 시계열을 EconomicIndicator로 동기화 (멱등).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--series', nargs='*', default=None,
            help='특정 series만 sync (default: VIX3M, MOVE)',
        )
        parser.add_argument(
            '--period', default='3mo',
            help='yfinance period (default 3mo, 백필 시 1y/2y 권장)',
        )

    def handle(self, *args, **options):
        import yfinance as yf

        from macro.models.indicators import EconomicIndicator, IndicatorValue

        series_codes: Iterable[str] = options['series'] or list(SERIES_MAP.keys())
        period = options['period']

        total_saved = 0
        total_failed = 0

        for code in series_codes:
            ticker = SERIES_MAP.get(code.upper())
            if ticker is None:
                self.stdout.write(self.style.WARNING(f'[skip] {code}: not in SERIES_MAP'))
                total_failed += 1
                continue

            try:
                indicator = EconomicIndicator.objects.get(code=code.upper())
            except EconomicIndicator.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'[skip] EconomicIndicator(code={code}) not seeded — run macro 0003 migration'
                ))
                total_failed += 1
                continue

            try:
                df = yf.download(
                    ticker,
                    period=period,
                    interval='1d',
                    progress=False,
                    auto_adjust=False,
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'[error] {code} ({ticker}): {exc}'))
                total_failed += 1
                continue

            if df is None or df.empty:
                self.stdout.write(self.style.WARNING(f'[empty] {code} ({ticker}): no data'))
                total_failed += 1
                continue

            saved = 0
            with transaction.atomic():
                for idx, row in df.iterrows():
                    obs_date = idx.date() if hasattr(idx, 'date') else idx
                    # df['Close']는 multi-column일 수 있음 (yfinance 1.3+)
                    close_val = row.get('Close')
                    if hasattr(close_val, 'item'):
                        try:
                            close_val = close_val.item()
                        except Exception:  # noqa: BLE001
                            close_val = float(close_val)
                    if close_val is None:
                        continue
                    try:
                        value = Decimal(str(close_val))
                    except (InvalidOperation, ValueError):
                        continue
                    _, created = IndicatorValue.objects.update_or_create(
                        indicator=indicator,
                        date=obs_date,
                        defaults={'value': value},
                    )
                    if created:
                        saved += 1

            indicator.last_updated = timezone.now()
            indicator.save(update_fields=['last_updated'])
            total_saved += saved
            self.stdout.write(self.style.SUCCESS(
                f'[ok] {code} ({ticker}): {saved} new (period={period})'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. total_saved={total_saved} total_failed={total_failed}'
        ))
