"""
StockLeadershipScore — 종목×테마×윈도우 주도주 지표 스냅샷 (CS-M2).

M1(StockAttentionScore)과 별개 신규 엔진. 종목 레벨 4지표만 영속:
  T2  trend_quality        (윈도우별, 테마무관)
  T3  theme_alpha / theme_beta (윈도우별, LOO 회귀, 테마 멤버<3 시 NULL)
  ②   up_capture / down_capture / capture_spread (윈도우별, LOO)

게이트 미달(유효 관측일 부족, 분모 0, 테마 멤버 부족)은 NULL 허용(에러 아님).
정규화는 표시단(serializer) — 여기엔 raw 보존.
T2·T3 단순 가산 금지 → 합성 단일점수 컬럼 없음(분리 노출).
"""

from django.db import models


class StockLeadershipScore(models.Model):
    """종목×테마×윈도우×일자 주도주 지표 스냅샷(CS-M2). 게이트 미달은 NULL."""

    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        to_field="symbol",
        db_column="symbol",
        related_name="leadership_scores",
    )
    theme = models.CharField(max_length=128, db_index=True)
    window = models.IntegerField(help_text="회귀/추세 윈도우 길이 (20 또는 120).")
    as_of_date = models.DateField(db_index=True)

    # ── 지표 (게이트 미달 시 NULL) ──
    trend_quality = models.FloatField(
        null=True, blank=True,
        help_text="T2: (slope×252)×R². 테마무관, 윈도우별.",
    )
    theme_alpha = models.FloatField(
        null=True, blank=True,
        help_text="T3: α×252. 테마 멤버<3 시 NULL.",
    )
    theme_beta = models.FloatField(
        null=True, blank=True,
        help_text="T3: β (r_i~α+β·r_theme_LOO). 테마 멤버<3 시 NULL.",
    )
    up_capture = models.FloatField(
        null=True, blank=True,
        help_text="② theme>0 일 Σr_i/Σr_theme×100. 분모 0 시 NULL.",
    )
    down_capture = models.FloatField(
        null=True, blank=True,
        help_text="② theme<0 일 Σr_i/Σr_theme×100. 분모 0 시 NULL.",
    )
    capture_spread = models.FloatField(
        null=True, blank=True,
        help_text="② up_capture − down_capture. 둘 중 하나라도 NULL이면 NULL.",
    )

    obs_count = models.IntegerField(
        default=0,
        help_text="윈도우 내 유효 관측(수익률)일 수.",
    )
    is_fallback = models.BooleanField(
        default=False,
        help_text="120일 미달로 20 윈도우만 산출된 종목 표시(IPO/상폐/프리미엄).",
    )
    benchmark_kind = models.CharField(
        max_length=24,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "벤치마크 피어셋 구성(additive). NULL=레거시 theme_tags LOO 경로. "
            "'core_loo'=EventGroup 코어 종목(코어 자기제외 LOO). "
            "'sat_coremean'=EventGroup 위성 종목(전체 코어 평균). "
            "새 경로 행은 theme='eg:{slug}'로 레거시 행과 키 분리(unique_together 미변경)."
        ),
    )

    class Meta:
        unique_together = [("stock", "theme", "window", "as_of_date")]
        indexes = [
            models.Index(fields=["as_of_date", "theme", "window"]),
            models.Index(fields=["as_of_date", "window", "-trend_quality"]),
        ]

    def __str__(self):
        return f"{self.stock_id} {self.theme} w{self.window} {self.as_of_date}"
