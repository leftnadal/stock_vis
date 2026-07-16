"""
SymbolCentrality — 일별 그래프 중심성 스냅샷 (⑲ S3, S-C 시나리오).

RelationConfidence 전량을 무방향 가중 그래프(가중치 truth_score)로 구성해
PageRank(허브) + betweenness(브리지)를 산출한 일별 append 스냅샷. ⑱ 조사에서
"유일하게 성립한 시나리오"로 판정된 중심성을 해자 궤적으로 적립한다.

- Neo4j 불사용: PG + networkx in-memory (⑱ 드라이런 3.92초 실증).
- 일별 append(궤적 보존): (symbol, as_of) unique, 덮어쓰기 금지·update_or_create 멱등.
- symbol은 CharField(RelationConfidence 정합) — Stock 미등재 심볼도 그래프 노드로 포함.
- 화면 노출은 별도 트랙(⑳). 본 모델·태스크·조회 API까지가 ⑲ 범위.
"""

from django.db import models


class SymbolCentrality(models.Model):
    """일별 종목 중심성 스냅샷(PageRank·betweenness + 순위 + 그래프 규모)."""

    symbol = models.CharField(max_length=10, db_index=True)
    as_of = models.DateField(db_index=True)

    # 중심성 원값 (truth_score 가중 무방향 그래프)
    pagerank = models.FloatField()
    betweenness = models.FloatField()

    # 그날 그래프 내 순위 (1 = 최상위)
    pagerank_rank = models.IntegerField()
    betweenness_rank = models.IntegerField()

    # 그래프 규모 스냅샷 (재현·드리프트 감사용)
    graph_nodes = models.IntegerField()
    graph_edges = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chainsight_symbol_centrality"
        unique_together = [("symbol", "as_of")]
        indexes = [
            models.Index(fields=["as_of", "pagerank_rank"]),      # 상위 PageRank 조회
            models.Index(fields=["as_of", "betweenness_rank"]),   # 상위 betweenness 조회
            models.Index(fields=["symbol", "-as_of"]),            # 심볼 궤적
        ]

    def __str__(self):
        return (
            f"{self.symbol}@{self.as_of} pr#{self.pagerank_rank}"
            f"/bt#{self.betweenness_rank}"
        )
