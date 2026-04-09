# Celery Beat 일괄 등록

> **완료일**: 2026-04-04

## 수정된 파일

| 파일 | 변경 |
|------|------|
| `config/celery.py` | beat_schedule에 11개 task 추가 + task_routes에 3개 Neo4j 큐 추가 |

## 등록된 스케줄 (11개)

### Chain Sight (8개)

| 이름 | Task | 스케줄 |
|------|------|--------|
| chainsight-all-profiles | profile_tasks.calculate_all_profiles | 토 02:00 |
| chainsight-co-mentions | relation_tasks.extract_co_mentions | 매일 10:00 |
| chainsight-price-co-movement | relation_tasks.calculate_price_co_movement | 토 03:00 |
| chainsight-relation-confidence | relation_tasks.update_relation_confidence | 매일 11:00 |
| chainsight-stale-decay | relation_tasks.check_stale_and_decay | 토 04:00 |
| chainsight-aggregate-profiles | sync_tasks.aggregate_chain_profiles | 토 04:30 |
| chainsight-sync-profiles-neo4j | sync_tasks.sync_profiles_to_neo4j | 매일 12:00 |
| chainsight-sync-relations-neo4j | sync_tasks.sync_relations_to_neo4j | 매일 12:30 |

### Validation (1개)

| 이름 | Task | 스케줄 |
|------|------|--------|
| validation-weekly-batch | tasks.run_weekly_validation_batch | 토 05:00 |

### SEC Pipeline (2개)

| 이름 | Task | 스케줄 |
|------|------|--------|
| sec-sync-dirty-neo4j | tasks.sync_dirty_to_neo4j | 5분마다 |
| sec-check-new-filings | tasks.check_new_filings | 매월 1일 06:00 |

## 토요일 파이프라인 순서

```
02:00  chainsight-all-profiles (GrowthStage+CapitalDNA+Sensitivity+Insider)
03:00  chainsight-price-co-movement
04:00  chainsight-stale-decay
04:30  chainsight-aggregate-profiles
05:00  validation-weekly-batch
```

## Neo4j 큐 라우팅 (추가 3개)

```
chainsight.tasks.sync_tasks.sync_profiles_to_neo4j → neo4j
chainsight.tasks.sync_tasks.sync_relations_to_neo4j → neo4j
sec_pipeline.tasks.sync_dirty_to_neo4j → neo4j
```

## 전체 Beat 스케줄

총 **80개** task 등록 (기존 69 + 신규 11)
