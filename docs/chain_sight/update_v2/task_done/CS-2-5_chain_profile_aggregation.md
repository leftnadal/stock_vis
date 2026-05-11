# CS-2-5: CompanyChainProfile 집약 + Celery Beat

> **완료일**: 2026-04-18
> **상태**: 이미 구현됨 — 검증 완료

## 결과

- **CompanyChainProfile**: 503건 ✅

### Celery Beat 스케줄 (10개 등록)

| # | 이름 | Task | 스케줄 |
|---|------|------|--------|
| 1 | chainsight-all-profiles | calculate_all_profiles | 토 02:00 |
| 2 | chainsight-co-mentions | extract_co_mentions | 매일 10:00 |
| 3 | chainsight-price-co-movement | calculate_price_co_movement | 토 03:00 |
| 4 | chainsight-relation-confidence | update_relation_confidence | 매일 11:00 |
| 5 | chainsight-stale-decay | check_stale_and_decay | 토 04:00 |
| 6 | chainsight-aggregate-profiles | aggregate_chain_profiles | 토 04:30 |
| 7 | chainsight-sync-profiles-neo4j | sync_profiles_to_neo4j | 매일 12:00 |
| 8 | chainsight-sync-relations-neo4j | sync_relations_to_neo4j | 매일 12:30 |
| 9 | chainsight-seed-selection | seed selection | 매일 13:00 |
| 10 | chainsight-neo4j-dirty-sync | dirty sync | 일 04:30 |

→ 다음: cs_31 (Phase 3 시작)
