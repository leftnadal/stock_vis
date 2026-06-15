"""
StockAttentionScore — 일별 종목 관심도 스냅샷 (M1: 거래 기반).

M1 = 0.50 × 거래량z-score(20일) + 0.30 × 변동성백분위 + 0.20 × 수익률백분위
컴포넌트 분리 저장 — M3(co-mention 결합) 승격 대비.
"""

from django.db import models


class StockAttentionScore(models.Model):
    """일별 종목 관심도 스냅샷(M1). M3 승격 대비 컴포넌트 분리 저장."""

    symbol = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        db_column="symbol",
        related_name="attention_scores",
    )
    date = models.DateField(db_index=True)
    score = models.FloatField()               # 0~100 최종 점수
    volume_z = models.FloatField()            # 20일 거래량 z-score
    volatility_pct = models.FloatField()      # 일중 변동성 cross-sectional 백분위(0~1)
    return_pct = models.FloatField()          # |수익률| cross-sectional 백분위(0~1)
    raw_return = models.FloatField()          # 부호 있는 수익률(표시용)
    is_low_liquidity = models.BooleanField(
        default=False,
        help_text="ADV < ADV_FLOOR 시 True. 점수는 정상 계산·저장(제외 아님).",
    )

    class Meta:
        unique_together = [("symbol", "date")]
        indexes = [
            models.Index(fields=["date", "-score"]),
        ]

    def __str__(self):
        return f"{self.symbol_id} {self.date} score={self.score}"
