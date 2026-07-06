# Graph Analysis — CUT (tombstone)

`graph_analysis`: **CUT 완료 (2026-07, D-REHOME-GRAPH)**. 휴면 상관관계 엔진(통계적 Pearson price-correlation + anomaly 탐지), 소비자 0·prod 0 rows로 제거.

- **코드 복구 SHA**: `f892d90` (앱 전량 1444줄 보존).
- **IP 스냅샷**: `CorrelationCalculator`(Watchlist→Pearson 상관행렬+엣지, networkx) · `AnomalyDetector`(상관 변동 이상탐지+알림 라이프사이클) — 상세는 `DECISIONS.md` "D-REHOME-GRAPH".
- 미래 통계상관/이상탐지 필요 시 위 SHA에서 소환. chain_sight 해자(RelationConfidence, 관계 발견)와 접근 상이.

> 이 파일은 grep 발견성 유지용 tombstone. 실제 코드·결정은 위 SHA·DECISIONS 참조.
