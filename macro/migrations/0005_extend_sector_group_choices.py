# PR-A1 (1/2 SCHEMA): MarketIndex.sector_group choices 확장
#   - 4종(BENCHMARK/SECTOR/SAFE_HAVEN/INTERNATIONAL) → 12종(BENCHMARK + GICS 11)
#   - max_length 20 → 32, db_index 추가, default '' → 'BENCHMARK'
# 데이터 매핑은 0006_remap_sector_group_to_gics.py에서 처리 (A-Ⅲ 3분리 정신).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('macro', '0004_seed_marketpulse_v2_indices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketindex',
            name='sector_group',
            field=models.CharField(
                max_length=32,
                choices=[
                    ('BENCHMARK', 'Benchmark'),
                    ('FINANCIALS', 'Financials'),
                    ('TECH', 'Technology'),
                    ('HEALTHCARE', 'Healthcare'),
                    ('CONSUMER_DISC', 'Consumer Discretionary'),
                    ('CONSUMER_STAPLES', 'Consumer Staples'),
                    ('ENERGY', 'Energy'),
                    ('INDUSTRIALS', 'Industrials'),
                    ('MATERIALS', 'Materials'),
                    ('UTILITIES', 'Utilities'),
                    ('REAL_ESTATE', 'Real Estate'),
                    ('COMMUNICATION', 'Communication Services'),
                ],
                default='BENCHMARK',
                db_index=True,
                help_text='Market Pulse v2 그룹 (BENCHMARK + GICS 11-sector). PR-C/G query 필터.',
            ),
        ),
    ]
