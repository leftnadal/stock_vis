"""MIG-BUNDLE-1 B-2: 레버리지 ETF 유니버스 제외 플래그 데이터 승격.

1단 임시 필터(chain_sight.UNIVERSE_EXCLUDED_INDUSTRIES = industry
"Asset Management - Leveraged")가 제외하던 **바로 그 집합**을 종목 단위 플래그로
승격한다. 선택 기준을 industry 멤버십으로 두어 전환 전후 제외 집합이 동일함을
보장(행위보존 — B-4). 실측(2026-08-31): 이 industry = 정확히 OKLL·IREG·GEVG 3종.

스키마 마이그(0017)와 분리된 데이터 마이그(하이브리드 DoD).
"""

from django.db import migrations

LEVERAGED_INDUSTRY = "Asset Management - Leveraged"
REASON = "LEVERAGED_ETF"


def flag_leveraged_etfs(apps, schema_editor):
    Stock = apps.get_model("stocks", "Stock")
    qs = Stock.objects.filter(industry=LEVERAGED_INDUSTRY)
    syms = sorted(qs.values_list("symbol", flat=True))
    n = qs.update(universe_excluded=True, exclude_reason=REASON)
    # 마이그 로그에 남지 않으므로 print 로 병진 가시화(전환 대상 확인).
    print(f"  [B-2] universe_excluded=True 설정: {n}행 {syms} (industry={LEVERAGED_INDUSTRY})")


def unflag(apps, schema_editor):
    Stock = apps.get_model("stocks", "Stock")
    Stock.objects.filter(exclude_reason=REASON).update(
        universe_excluded=False, exclude_reason=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0017_stock_universe_excluded_flag"),
    ]

    operations = [
        migrations.RunPython(flag_leveraged_etfs, unflag),
    ]
