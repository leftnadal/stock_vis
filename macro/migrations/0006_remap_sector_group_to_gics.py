# PR-A1 (2/2 DATA): 기존 4종 sector_group → GICS 12종 매핑
#   - 'SECTOR' (XL* 11개) → 각 GICS sector (XLF→FINANCIALS, XLK→TECH, ...)
#   - 'BENCHMARK'/'SAFE_HAVEN'/'INTERNATIONAL'/'' (default) → 'BENCHMARK' (default 흡수)
# Idempotent: 동일 매핑 재실행 시 변경 0.
# A-Ⅲ 3분리 정신: SCHEMA(0005)와 DATA(0006) 분리, 부분 reverse 가능.
from django.db import migrations

# ============================================================
# HARDCODED MAPPING (Decision B-Ⅰ — 변경은 새 migration 작성)
# ============================================================

# XL* sector ETF symbol → GICS sector group
GICS_SYMBOL_MAPPING = {
    'XLF': 'FINANCIALS',
    'XLK': 'TECH',
    'XLV': 'HEALTHCARE',
    'XLY': 'CONSUMER_DISC',
    'XLP': 'CONSUMER_STAPLES',
    'XLE': 'ENERGY',
    'XLI': 'INDUSTRIALS',
    'XLB': 'MATERIALS',
    'XLU': 'UTILITIES',
    'XLRE': 'REAL_ESTATE',
    'XLC': 'COMMUNICATION',
}

# 역매핑 (reverse 시 GICS → 'SECTOR'로 일괄 복귀)
GICS_TO_LEGACY = {v: k for k, v in GICS_SYMBOL_MAPPING.items()}

assert len(GICS_SYMBOL_MAPPING) == 11, 'GICS 11-sector 매핑은 정확히 11개여야 함'


def forward(apps, schema_editor):
    """4종 → 12종 매핑.
    - XL* 11개: symbol 기반 GICS sector 매핑
    - 기타(SECTOR가 아닌 모든 row): default 'BENCHMARK'로 흡수
    """
    MarketIndex = apps.get_model('macro', 'MarketIndex')

    # XL* sector ETFs: GICS 매핑
    for symbol, gics in GICS_SYMBOL_MAPPING.items():
        MarketIndex.objects.filter(symbol=symbol).update(sector_group=gics)

    # 그 외 (BENCHMARK/SAFE_HAVEN/INTERNATIONAL/'' 등): BENCHMARK로 흡수
    MarketIndex.objects.exclude(
        symbol__in=list(GICS_SYMBOL_MAPPING.keys())
    ).exclude(sector_group='BENCHMARK').update(sector_group='BENCHMARK')


def reverse(apps, schema_editor):
    """역연산: GICS 11종 → 'SECTOR' 일괄 복귀.
    - 'SAFE_HAVEN'/'INTERNATIONAL' 의미는 복원 불가 (default 'BENCHMARK'로 흡수됨).
    - 0005 schema reverse 시 max_length=32 → 20으로 축소되므로 'COMMUNICATION'(13자)는 안전.
    """
    MarketIndex = apps.get_model('macro', 'MarketIndex')
    for symbol in GICS_SYMBOL_MAPPING:
        MarketIndex.objects.filter(symbol=symbol).update(sector_group='SECTOR')


class Migration(migrations.Migration):

    dependencies = [
        ('macro', '0005_extend_sector_group_choices'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
