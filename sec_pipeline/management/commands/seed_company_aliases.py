"""
CompanyAlias 시드 데이터 + 주요 외국 기업 Stock 생성.

Usage:
    python manage.py seed_company_aliases
    python manage.py seed_company_aliases --dry-run
"""

import logging

from django.core.management.base import BaseCommand

from packages.shared.stocks.models import Stock
from sec_pipeline.models import CompanyAlias

logger = logging.getLogger(__name__)

# 기존 Stock DB에 있는 기업의 별칭
ALIAS_SEEDS = [
    # (alias, ticker, sector)
    ('Micron Technology, Inc.', 'MU', 'Technology'),
    ('Micron Technology', 'MU', 'Technology'),
    ('Micron', 'MU', 'Technology'),
    ('UnitedHealthcare', 'UNH', 'Healthcare'),
    ('Walmart', 'WMT', 'Consumer Defensive'),
    ('Walmart Inc.', 'WMT', 'Consumer Defensive'),
    ('Goldman Sachs', 'GS', 'Financial Services'),
    ('Apple', 'AAPL', 'Technology'),
    ('Microsoft', 'MSFT', 'Technology'),
    ('Google', 'GOOGL', 'Technology'),
    ('Amazon', 'AMZN', 'Consumer Cyclical'),
    ('Meta', 'META', 'Technology'),
    ('Meta Platforms', 'META', 'Technology'),
    ('Intel', 'INTC', 'Technology'),
    ('Intel Corporation', 'INTC', 'Technology'),
    ('AMD', 'AMD', 'Technology'),
    ('Advanced Micro Devices', 'AMD', 'Technology'),
    ('Qualcomm', 'QCOM', 'Technology'),
    ('Broadcom', 'AVGO', 'Technology'),
    ('Texas Instruments', 'TXN', 'Technology'),
    ('Oracle', 'ORCL', 'Technology'),
    ('Salesforce', 'CRM', 'Technology'),
    ('Adobe', 'ADBE', 'Technology'),
    ('Nvidia', 'NVDA', 'Technology'),
    ('NVIDIA Corporation', 'NVDA', 'Technology'),
]

# Stock DB에 없는 주요 외국 기업 — Stock 레코드 수동 생성
FOREIGN_STOCKS = [
    # (symbol, name, sector, industry, exchange)
    ('TSM', 'Taiwan Semiconductor Manufacturing Company Limited', 'Technology', 'Semiconductors', 'NYSE'),
    ('FN', 'Fabrinet', 'Technology', 'Electronic Components', 'NYSE'),
]

# Stock DB에 없고 OTC/비상장인 기업 — CompanyAlias만 등록 (매칭은 불가하지만 기록)
FOREIGN_ALIASES_NO_STOCK = [
    # (alias, note) — Stock이 없으므로 ticker='_FOREIGN_'+name
    ('Samsung', 'Samsung Electronics — OTC: SSNLF'),
    ('Samsung Electronics Co., Ltd.', 'Samsung Electronics — OTC: SSNLF'),
    ('SK Hynix Inc.', 'SK Hynix — OTC: HXSCF'),
    ('Hon Hai Precision Industry Co., Ltd.', 'Hon Hai/Foxconn — OTC: HNHPF'),
    ('Wistron Corporation', 'Wistron — TWSE'),
]


class Command(BaseCommand):
    help = 'CompanyAlias 시드 데이터 + 주요 외국 기업 Stock 생성'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # 1. 외국 기업 Stock 생성
        stock_created = 0
        for symbol, name, sector, industry, exchange in FOREIGN_STOCKS:
            if Stock.objects.filter(symbol=symbol).exists():
                self.stdout.write(f'  Stock {symbol} already exists, skipping')
                continue
            if not dry_run:
                Stock.objects.create(
                    symbol=symbol,
                    stock_name=name,
                    sector=sector,
                    industry=industry,
                    exchange=exchange,
                )
            stock_created += 1
            self.stdout.write(f'  Created Stock: {symbol} ({name})')

        # 2. CompanyAlias 시드 — sector 한정 + 범용(context_sector='') 둘 다 등록
        # 2026-05-26: queue 항목의 source_sectors가 alias seed sector와 다를 때도
        # 매칭되도록 범용(context_sector='')을 함께 등록. 예: 'Google'은 Technology로
        # 등록되지만, queue에서 Communication Services로 등장 시 범용에 fallback.
        alias_created = 0
        for alias, ticker, sector in ALIAS_SEEDS:
            if not Stock.objects.filter(symbol=ticker).exists():
                self.stdout.write(f'  Stock {ticker} not found, skipping alias "{alias}"')
                continue
            for ctx in (sector, ''):
                obj, created = CompanyAlias.objects.get_or_create(
                    alias=alias,
                    context_sector=ctx,
                    defaults={
                        'ticker': ticker,
                        'source': 'seed',
                    },
                ) if not dry_run else (None, True)
                if created:
                    alias_created += 1

        # 3. 외국 기업 CompanyAlias (Stock 생성된 것만)
        for symbol, name, sector, industry, exchange in FOREIGN_STOCKS:
            if not dry_run:
                CompanyAlias.objects.get_or_create(
                    alias=name,
                    context_sector=sector,
                    defaults={'ticker': symbol, 'source': 'seed'},
                )
                # 약칭도 등록
                short_name = name.split(',')[0].split(' Limited')[0].strip()
                if short_name != name:
                    CompanyAlias.objects.get_or_create(
                        alias=short_name,
                        context_sector=sector,
                        defaults={'ticker': symbol, 'source': 'seed'},
                    )
                alias_created += 1

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Stock created: {stock_created}, Alias created: {alias_created}'
        ))
