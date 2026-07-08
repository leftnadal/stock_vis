"""
관계 쌍 스냅샷 (해자 궤적 적립 — 옵션3).

RelationConfidence는 unique_together=(symbol_a, symbol_b, relation_type)이라
한 행은 truth 또는 market 중 하나만 갖는다(per-row 합성 불가). 또한 주간 배치가
update_or_create defaults로 점수를 덮어써 과거 점이 소실된다(궤적 부재).

이 모델은 정규화 쌍(canonical (a,b)) 단위로 truth_max/market_max를 집계하고,
relevance_opp/relevance_risk를 [0,1]로 파생해 period별로 append한다.
  - 현재값  = 쌍별 최신 period 스냅샷 (DISTINCT ON)
  - 누적     = 해자의 시계열 궤적 + 상향 학습 루프의 입력 재료(forward-only 적립)

집계는 RelationConfidence.relation_category('truth'|'market')로 분기하므로
새 relation_type이 생겨도 이 경로는 수정 불필요하다.
"""

from django.db import models


class RelationPairSnapshot(models.Model):
    # 정규화 쌍 키: 항상 normalize_pair(=sorted)로 저장 (무방향)
    canonical_a = models.CharField(max_length=16, db_index=True)
    canonical_b = models.CharField(max_length=16, db_index=True)
    period = models.DateField()  # 그 주의 기준일(배치 실행일)

    truth_max = models.FloatField()   # 0..100
    market_max = models.FloatField()  # 0..100
    relevance_opp = models.FloatField()   # [0,1]
    relevance_risk = models.FloatField()  # [0,1]

    # 동점(계단값) 2차 정렬용 보강도
    truth_edge_count = models.IntegerField(default=0)
    market_edge_count = models.IntegerField(default=0)

    last_observed_at = models.DateTimeField(null=True)  # 쌍 내 최신 관측 시각
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chainsight_relation_pair_snapshot"
        unique_together = ("canonical_a", "canonical_b", "period")  # 멱등 upsert
        indexes = [
            models.Index(fields=["canonical_a", "canonical_b", "-period"]),  # 최신 단면
            models.Index(fields=["-relevance_opp", "-period"]),   # 발견 정렬
            models.Index(fields=["-relevance_risk", "-period"]),  # 경고 정렬
        ]

    def __str__(self):
        return (
            f"{self.canonical_a}↔{self.canonical_b} @{self.period}: "
            f"opp={self.relevance_opp:.3f} risk={self.relevance_risk:.3f}"
        )
