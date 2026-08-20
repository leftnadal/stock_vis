from django.db import migrations


class Migration(migrations.Migration):
    """0014 리프 통합 (그래프 reconcile, no-op DDL).

    CS-P3의 0014_stock_cik(Stock.cik)와 타트랙 0014_stocksplit(StockSplit 모델)이
    둘 다 0013에서 분기 → 리프 2개. 둘 다 공유 DB에 이미 적용됨(2026-08-13).
    본 머지는 그래프를 단일 리프로 통합만 하며 스키마 변경 없음.
    """

    dependencies = [
        ("stocks", "0014_stock_cik"),
        ("stocks", "0014_stocksplit"),
    ]

    operations = []
