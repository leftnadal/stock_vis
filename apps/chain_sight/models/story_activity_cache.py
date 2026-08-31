"""R2-S2 선행 캐시: 종목별 co-mention 파트너 활동 일일 물질화(MIG-BUNDLE-1 C).

story_activity.get_symbol_story_threads 의 라이브 집계(특히 NewsEntity 7일 집계)를
일일 스냅샷으로 물질화한다. 카드 API 는 이 캐시를 소스로 하고, 부재/미갱신 시
라이브로 fallback(빈 화면 금지). 전역 activity_ratio 정렬(S2 활동 뷰)의 소스이기도 하다.

한 행 = (symbol, partner) 최신 스냅샷(일일 upsert, 이력 미보존).
"""

from django.db import models


class SymbolStoryActivity(models.Model):
    symbol = models.CharField(max_length=10, db_index=True)
    partner = models.CharField(max_length=10)

    count_7d = models.IntegerField(default=0)
    count_90d = models.IntegerField(default=0)
    weekly_avg_90d = models.FloatField(default=0.0)
    # c7/weekly_avg. weekly_avg=0(기저 없음)이면 null(게이지 대신 "조용함" 표시).
    activity_ratio = models.FloatField(null=True, blank=True)
    last_co_mention_date = models.DateField(null=True, blank=True)

    # 종목 단위 총 파트너 수(denormalized) — 캐시만으로 threads_capped 계산.
    thread_total = models.IntegerField(default=0)
    # 물질화 시각(신선도 판정 — 미갱신 시 라이브 fallback).
    materialized_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chainsight_symbol_story_activity"
        unique_together = ("symbol", "partner")
        indexes = [
            models.Index(fields=["symbol"]),  # 카드 lookup
            models.Index(fields=["-activity_ratio"]),  # 전역 활동 상위 정렬(S2)
            models.Index(fields=["symbol", "-count_7d"]),  # 카드 활동순
        ]

    def __str__(self):
        return f"{self.symbol}→{self.partner}: 7d={self.count_7d} ratio={self.activity_ratio}"
