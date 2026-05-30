"""Seed 20 MarketIndex rows + sector_group for Market Pulse v2 (PR-A1)."""
from django.db import migrations

INDICES = [
    # BENCHMARK 4
    ('SPY', 'S&P 500 ETF', 'us_equity', 'BENCHMARK'),
    ('QQQ', 'NASDAQ 100 ETF', 'us_equity', 'BENCHMARK'),
    ('DIA', 'Dow Jones ETF', 'us_equity', 'BENCHMARK'),
    ('IWM', 'Russell 2000 ETF', 'us_equity', 'BENCHMARK'),
    # SECTOR 11 (SPDR)
    ('XLK', 'Technology Sector', 'sector', 'SECTOR'),
    ('XLF', 'Financial Sector', 'sector', 'SECTOR'),
    ('XLV', 'Health Care Sector', 'sector', 'SECTOR'),
    ('XLE', 'Energy Sector', 'sector', 'SECTOR'),
    ('XLI', 'Industrial Sector', 'sector', 'SECTOR'),
    ('XLY', 'Consumer Discretionary Sector', 'sector', 'SECTOR'),
    ('XLP', 'Consumer Staples Sector', 'sector', 'SECTOR'),
    ('XLU', 'Utilities Sector', 'sector', 'SECTOR'),
    ('XLB', 'Materials Sector', 'sector', 'SECTOR'),
    ('XLRE', 'Real Estate Sector', 'sector', 'SECTOR'),
    ('XLC', 'Communication Services Sector', 'sector', 'SECTOR'),
    # SAFE_HAVEN 4
    ('GLD', 'Gold ETF', 'commodity', 'SAFE_HAVEN'),
    ('SLV', 'Silver ETF', 'commodity', 'SAFE_HAVEN'),
    ('TLT', '20+ Year Treasury Bond ETF', 'bond', 'SAFE_HAVEN'),
    ('UUP', 'US Dollar Index ETF', 'currency', 'SAFE_HAVEN'),
    # INTERNATIONAL 1
    ('VEA', 'Developed Markets ex-US ETF', 'global_equity', 'INTERNATIONAL'),
]


def seed_forward(apps, schema_editor):
    MarketIndex = apps.get_model('macro', 'MarketIndex')
    for symbol, name, category, sector_group in INDICES:
        MarketIndex.objects.update_or_create(
            symbol=symbol,
            defaults={
                'name': name,
                'category': category,
                'sector_group': sector_group,
                'fmp_symbol': symbol,
                'is_active': True,
            },
        )


def seed_reverse(apps, schema_editor):
    """rollback: 본 마이그레이션이 추가한 20 row만 sector_group을 ''로 되돌린다 (row 보존)."""
    MarketIndex = apps.get_model('macro', 'MarketIndex')
    MarketIndex.objects.filter(
        symbol__in=[i[0] for i in INDICES],
    ).update(sector_group='')


class Migration(migrations.Migration):

    dependencies = [
        ('macro', '0003_seed_marketpulse_v2_indicators'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
