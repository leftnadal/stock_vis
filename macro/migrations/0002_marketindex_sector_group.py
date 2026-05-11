"""Add MarketIndex.sector_group for Market Pulse v2 (PR-A1)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('macro', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketindex',
            name='sector_group',
            field=models.CharField(
                blank=True,
                choices=[
                    ('BENCHMARK', 'Benchmark'),
                    ('SECTOR', 'Sector'),
                    ('SAFE_HAVEN', 'Safe Haven'),
                    ('INTERNATIONAL', 'International'),
                ],
                default='',
                help_text='Market Pulse v2 그룹 (BENCHMARK/SECTOR/SAFE_HAVEN/INTERNATIONAL)',
                max_length=20,
            ),
        ),
    ]
