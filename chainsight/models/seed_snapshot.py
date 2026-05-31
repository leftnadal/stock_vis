"""
SeedSnapshot — 일자별 Chain Sight 시드 선정 결과 영속 저장소.

Redis 캐시가 휘발(테스트 flush, 재시작, TTL 만료 등)되어도 운영 데이터가 보존되도록
PostgreSQL에 스냅샷을 남긴다. Redis는 hot-path 가속 레이어로만 유지한다.
"""

from django.db import models


class SeedSnapshot(models.Model):
    market_date = models.DateField(
        unique=True,
        db_index=True,
        help_text="시드 대상 시장일(NYSE 기준).",
    )
    payload = models.JSONField(
        help_text="SeedListView 응답 전체 구조(date/total_seeds/sector_summary/seeds).",
    )
    total_seeds = models.PositiveIntegerField(default=0)
    sector_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-market_date"]
        indexes = [
            models.Index(fields=["-market_date"], name="seed_snap_date_desc_idx"),
        ]

    def __str__(self):
        return f"SeedSnapshot({self.market_date}, seeds={self.total_seeds})"
