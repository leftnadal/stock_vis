# CS-2-5: CompanyChainProfile 집계

> **완료일**: 2026-04-03

## 생성/수정된 파일

- `chainsight/tasks/sync_tasks.py` (aggregate_chain_profiles)

## 결과

- CompanyChainProfile: **503건** (S&P 500 전체)
- GrowthStage + CapitalDNA + 관계 통계를 하나의 프로파일로 집계
- neo4j_synced 필드 포함 (Phase 3 동기화 준비)

### 집계 필드

| 필드 | 원천 | 설명 |
|------|------|------|
| growth_stage | CompanyGrowthStage | mature/accelerating/declining 등 |
| capital_type | CompanyCapitalDNA | balanced/heavy_investor 등 |
| relation_count | RelationConfidence | confirmed+probable 관계 수 |
| peer_count | PEER_OF 관계 | 직접 피어 수 |
| sector, industry | Stock 모델 | 분류 |

## 다음 작업

→ CS-3-1: Profile → Neo4j 동기화
