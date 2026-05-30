"""Seed 11 EconomicIndicator series for Market Pulse v2 (PR-A1)."""
from django.db import migrations

SERIES = [
    ('NFCI', 'Chicago Fed National Financial Conditions Index', 'sentiment', 'fred', 'weekly'),
    ('NFCICREDIT', 'NFCI Credit Subindex', 'sentiment', 'fred', 'weekly'),
    ('NFCILEVERAGE', 'NFCI Leverage Subindex', 'sentiment', 'fred', 'weekly'),
    ('NFCIRISK', 'NFCI Risk Subindex', 'sentiment', 'fred', 'weekly'),
    ('BAMLH0A0HYM2', 'ICE BofA US High Yield Index Option-Adjusted Spread', 'interest_rate', 'fred', 'daily'),
    ('BAMLH0A3HYC', 'ICE BofA CCC & Lower US HY OAS', 'interest_rate', 'fred', 'daily'),
    ('T10Y3M', '10-Year Treasury Minus 3-Month Treasury', 'interest_rate', 'fred', 'daily'),
    ('VIX3M', 'CBOE 3-Month Volatility Index', 'volatility', 'fred', 'daily'),
    ('MOVE', 'ICE BofAML MOVE Index', 'volatility', 'fred', 'daily'),
    ('DGS10', 'DGS10', 'interest_rate', 'fred', 'daily'),
    ('DGS2', 'DGS2', 'interest_rate', 'fred', 'daily'),
]


def seed_forward(apps, schema_editor):
    EconomicIndicator = apps.get_model('macro', 'EconomicIndicator')
    for code, name, category, source, freq in SERIES:
        EconomicIndicator.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'category': category,
                'data_source': source,
                'update_frequency': freq,
                'is_active': True,
            },
        )


def seed_reverse(apps, schema_editor):
    """rollback: 본 마이그레이션이 추가한 11 series만 삭제 (기존 row 보존)."""
    EconomicIndicator = apps.get_model('macro', 'EconomicIndicator')
    EconomicIndicator.objects.filter(
        code__in=[s[0] for s in SERIES],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('macro', '0002_marketindex_sector_group'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
