# TH-7d (결정12b=A) — 섹터 SPDR 레버리지 짝(role=leveraged) 시드 9종.
#
# 설계 앵커 v1.2.4 §6.4 확정 매핑(정본). 유동성 하한 = 20일 중위 거래대금 ≥ $1M,
# 배율 = 3x 우선 + 3x 부재·부적격 섹터 2x 대체. XLB·XLC = 레버리지 결측 확정(미시드, §3-5).
#
# ⚠️ ERX(Energy, leveraged, 2x)는 0016 에 active=False 로 존재 → active=True 승격 +
#    measured_liquidity_usd 기록(신규 행 금지, update_or_create). 기존 inactive 레버리지
#    (SOXL·TQQQ) 등 나머지는 불변.
#
# measured_liquidity_usd = TH-7c 12b 프로브 실측 20일 중위 거래대금(감사용 스냅샷, 자동
# 갱신·보정 없음). 멱등: update_or_create(theme, etf_symbol, role).

from django.db import migrations

# (HeatEntity.ref_id[GICS], 레버리지 심볼, 배율, 실측 20d중위 거래대금 USD) — 9종 정본.
SPDR_LEVERAGED_SEED = [
    ("Technology",             "TECL", 3, 218_300_000),
    ("Financial Services",     "FAS",  3,  89_200_000),
    ("Energy",                 "ERX",  2,  30_900_000),  # 기존 행 승격
    ("Real Estate",            "DRN",  3,  13_500_000),
    ("Healthcare",             "CURE", 3,  10_000_000),
    ("Utilities",              "UTSL", 3,   4_900_000),
    ("Industrials",            "DUSL", 3,   2_000_000),
    ("Consumer Cyclical",      "WANT", 3,   1_100_000),
    ("Consumer Defensive",     "UGE",  2,   1_400_000),
    # XLB(Basic Materials)·XLC(Communication Services) = 레버리지 결측 확정(미시드).
]


def seed_spdr_leveraged(apps, schema_editor):
    """레버리지 9종(role=leveraged, active=True) 시드 + ERX 승격. 멱등."""
    HeatEntity = apps.get_model("chainsight", "HeatEntity")
    ThemeEtfMap = apps.get_model("chainsight", "ThemeEtfMap")

    for ref_id, symbol, mult, liq in SPDR_LEVERAGED_SEED:
        entity = HeatEntity.objects.get(kind="sector", ref_id=ref_id)
        ThemeEtfMap.objects.update_or_create(
            theme=entity,
            etf_symbol=symbol,
            role="leveraged",
            defaults={
                "leverage_factor": mult,
                "active": True,
                "measured_liquidity_usd": liq,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("chainsight", "0020_themeetfmap_measured_liquidity_usd_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_spdr_leveraged, migrations.RunPython.noop),
    ]
