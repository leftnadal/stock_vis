"""
FX 환율 저장 모델 — 앱 불가지론 범용 재료 (packages/shared/fx).

SLICE19B: KRW numéraire 토대. USD/KRW 등 통화쌍의 일간 종가 환율을 영속.
수집은 shared FMP 래퍼 경유(services.py). shared는 apps.*를 모른다(한 방향 규칙).
과설계 금지 — 현재 USD/KRW만, OHLC·다통화쌍 선반영 안 함(필요 시 19c+).
"""

from django.db import models


class ExchangeRate(models.Model):
    """통화쌍 일간 환율(종가). `unique(pair, date)`."""

    pair = models.CharField(
        max_length=7,
        default="USDKRW",
        db_index=True,
        help_text="통화쌍 (예: USDKRW = 1 USD당 KRW).",
    )
    date = models.DateField(help_text="환율 일자 (영업일).")
    close = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="종가 환율.",
    )
    source = models.CharField(
        max_length=20,
        default="fmp",
        help_text="데이터 출처.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "fx"
        db_table = "fx_exchange_rate"
        unique_together = ("pair", "date")
        indexes = [models.Index(fields=["pair", "-date"])]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.pair} {self.date}: {self.close}"
