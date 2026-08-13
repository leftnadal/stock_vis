"""MPS-1 MP-STRESS — 신규 수집 2종 EconomicIndicator seed (DTWEXBGS·STLFSI4).

D-MPS-INDICATORS: 위기/스트레스 감지 후보 계열을 **수집만 개시**(스코어 미편입).
  - DTWEXBGS: Nominal Broad US Dollar Index (daily) — 달러 유동성.
  - STLFSI4:  St. Louis Fed Financial Stress Index (weekly) — 검증 전용(Part4 STLFSI4 크로스체크).
  - SOFR 스프레드는 **배선 보류**(MPS-SOFR 별건: market_pulse 파생 인프라 부재·series 전략 미확정).
data_source='fred' 정확 기재(VIX3M·MOVE 라벨 오기재 전례 회피 — 둘 다 진짜 FRED).
편입 심사(Tier1+2)는 S4-REBASE. 이 행 자체는 데이터일 뿐 스키마 무변경(get_or_create 경로 skip 방지용).
"""
from django.db import migrations

SERIES = [
    ('DTWEXBGS', 'Nominal Broad U.S. Dollar Index', 'trade', 'fred', 'daily'),
    ('STLFSI4', 'St. Louis Fed Financial Stress Index (4th ed.)', 'sentiment', 'fred', 'weekly'),
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
    """rollback: 본 마이그레이션이 추가한 2 series만 삭제 (기존 row·IndicatorValue 보존)."""
    EconomicIndicator = apps.get_model('macro', 'EconomicIndicator')
    EconomicIndicator.objects.filter(code__in=[s[0] for s in SERIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('macro', '0006_remap_sector_group_to_gics'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
