"""
Market Pulse v2에 필요한 11 신규 EconomicIndicator series를 FRED에서 sync.

PR-A1 시드된 series:
    NFCI, NFCICREDIT, NFCILEVERAGE, NFCIRISK
    BAMLH0A0HYM2, BAMLH0A3HYC
    T10Y3M, VIX3M, MOVE
    + 기존 시드 보강 (DGS10, DGS2)

기존 `sync_all_indicators`(macro/services/macro_service.py)는 하드코딩된 8 series만 처리하므로,
본 커맨드는 v2 신규 series만 명시적으로 sync한다.

사용:
    python manage.py sync_marketpulse_v2_indicators                  # 기본 limit=100
    python manage.py sync_marketpulse_v2_indicators --limit 365      # 약 1년 백필
    python manage.py sync_marketpulse_v2_indicators --series NFCI MOVE --limit 365  # 일부만
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


V2_SERIES_DEFAULT = (
    'NFCI', 'NFCICREDIT', 'NFCILEVERAGE', 'NFCIRISK',
    'BAMLH0A0HYM2', 'BAMLH0A3HYC',
    'T10Y3M', 'VIX3M', 'MOVE',
    # 기존 series 보강 (운영 누락분 재충전 시 도움)
    'DGS10', 'DGS2',
)


class Command(BaseCommand):
    help = 'Market Pulse v2 11 신규 EconomicIndicator를 FRED에서 sync (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--series', nargs='*', default=None,
            help='특정 series만 sync (default: V2_SERIES_DEFAULT 11개)',
        )
        parser.add_argument(
            '--limit', type=int, default=100,
            help='시리즈당 fetch할 observation 수 (default 100, 백필 시 365 권장)',
        )

    def handle(self, *args, **options):
        from macro.models.indicators import EconomicIndicator, IndicatorValue
        from packages.shared.api_request.fred_client import FREDClient

        series_codes: Iterable[str] = options['series'] or V2_SERIES_DEFAULT
        limit = options['limit']

        client = FREDClient()
        total_saved = 0
        total_failed = 0

        for code in series_codes:
            try:
                indicator = EconomicIndicator.objects.get(code=code)
            except EconomicIndicator.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'[skip] EconomicIndicator(code={code}) not seeded — run macro 0003 migration'
                ))
                total_failed += 1
                continue

            try:
                observations = client.get_series_observations(
                    code, limit=limit, sort_order='desc',
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'[error] {code}: {exc}'))
                total_failed += 1
                continue

            saved = 0
            with transaction.atomic():
                for obs in observations:
                    date_str = obs.get('date')
                    value_str = obs.get('value')
                    if not date_str or not value_str or value_str == '.':
                        continue
                    try:
                        obs_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        value = Decimal(value_str)
                        _, created = IndicatorValue.objects.update_or_create(
                            indicator=indicator,
                            date=obs_date,
                            defaults={'value': value},
                        )
                        if created:
                            saved += 1
                    except (InvalidOperation, ValueError) as exc:
                        logger.warning('skip %s @ %s: %s', code, date_str, exc)
                        continue

            indicator.last_updated = timezone.now()
            indicator.save(update_fields=['last_updated'])
            total_saved += saved
            self.stdout.write(self.style.SUCCESS(
                f'[ok] {code}: {saved} new (limit={limit})'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. total_saved={total_saved} total_failed={total_failed}'
        ))
