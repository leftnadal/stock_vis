# TH-7c (결정12a) — 섹터 SPDR 11종 원본(role=primary) 시드.
#
# 설계 앵커 v1.2.3 §6.4: Cycle 1 C5 주 데이터 = 섹터 SPDR 11종(원본 전수). 레버리지 짝은
# TH-C5-SPDR-LEVERAGED(12b) 비준 후 별도 시드 — 이 migration 은 **원본만**.
#
# 결정12a 조건(시드 전 FMP 프로브 전수 통과)은 TH-7c STEP 0 에서 충족(11/11 존재+3년 이력).
#
# ⚠️ XLE(Energy)·XLV(Healthcare)는 0016 테마 ETF 9행에 이미 존재(active=False). 이 둘은
#    섹터 SPDR 원본이기도 하므로 role=primary·active=True 로 **승격**(update_or_create).
#    순수 테마 ETF 7행(SOXX/SMH/SOXL/QQQ/TQQQ/ITA/ERX)은 active=False 불변.
#
# 멱등: update_or_create(theme, etf_symbol, role) — 재실행 = 동일값 set = 무변화.

from django.db import migrations

# (HeatEntity.ref_id [GICS 정본, 0016 GICS_SECTORS], SPDR 원본 심볼) — 11 섹터 1:1 대응.
SPDR_PRIMARY_SEED = [
    ("Technology", "XLK"),
    ("Financial Services", "XLF"),
    ("Energy", "XLE"),
    ("Healthcare", "XLV"),
    ("Industrials", "XLI"),
    ("Consumer Cyclical", "XLY"),
    ("Consumer Defensive", "XLP"),
    ("Utilities", "XLU"),
    ("Basic Materials", "XLB"),
    ("Real Estate", "XLRE"),
    ("Communication Services", "XLC"),
]


def seed_spdr_primary(apps, schema_editor):
    """SPDR 11종 원본(role=primary, active=True) 시드. XLE/XLV 승격 포함. 멱등."""
    HeatEntity = apps.get_model("chainsight", "HeatEntity")
    ThemeEtfMap = apps.get_model("chainsight", "ThemeEtfMap")

    for ref_id, symbol in SPDR_PRIMARY_SEED:
        entity = HeatEntity.objects.get(kind="sector", ref_id=ref_id)
        ThemeEtfMap.objects.update_or_create(
            theme=entity,
            etf_symbol=symbol,
            role="primary",
            defaults={"leverage_factor": 1, "active": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("chainsight", "0017_universesnapshot"),
    ]

    operations = [
        # 비파괴 data-only. reverse = noop(신규 행 잔존 허용 — 파괴적 롤백 금지 관례).
        migrations.RunPython(seed_spdr_primary, migrations.RunPython.noop),
    ]
