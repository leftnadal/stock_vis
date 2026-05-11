# CS-2-5: CompanyChainProfile 집약 + Celery Beat 등록

> **작업 번호**: CS-2-5
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: 프로파일 + 관계 → 집약 테이블 + Celery Beat 9개 스케줄 등록
> **예상 소요**: 1~2일
> **선행 조건**: CS-2-4 완료
> **산출물**: `chainsight/tasks/sync_tasks.py` + Celery Beat 설정

---

## 집약 로직

1. Tier A 테이블들(GrowthStage, CapitalDNA, etc.)에서 점수 읽기
2. validation/CategorySignal에서 score_profitability 등 읽기 (서비스 레이어)
3. CompanyChainProfile 30개 필드 upsert
4. `neo4j_synced = False` 설정 (CS-3-1이 처리)

## Celery Beat 전체 등록 (8개)

```python
# config/settings.py 또는 config/celery.py
CELERY_BEAT_SCHEDULE = {
    # Chain Sight — 일간
    'chainsight-co-mention-daily': {
        'task': 'chainsight.tasks.extract_co_mentions',
        'schedule': crontab(hour=6, minute=30),
    },
    'chainsight-heat-score-daily': {
        'task': 'chainsight.tasks.calculate_heat_scores',
        'schedule': crontab(hour=7, minute=0),
        # 시드 노드용 heat_score 계산 → Neo4j :Stock 노드 속성 저장
    },
    # 주간 — 일요일 (5개)
    'chainsight-profiles-weekly': {
        'task': 'chainsight.tasks.calculate_all_profiles',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
    },
    'chainsight-price-comovement-weekly': {
        'task': 'chainsight.tasks.calculate_price_co_movement',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    'chainsight-relation-confidence-weekly': {
        'task': 'chainsight.tasks.update_relation_confidence',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
    },
    'chainsight-stale-decay-weekly': {
        'task': 'chainsight.tasks.check_stale_and_decay',
        'schedule': crontab(hour=4, minute=30, day_of_week=0),
    },
    'chainsight-chain-profile-weekly': {
        'task': 'chainsight.tasks.aggregate_chain_profiles',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),
    },
    # 동기화 — 일요일 (2개, Phase 3에서 구현)
    'chainsight-sync-profiles-weekly': {
        'task': 'chainsight.tasks.sync_profiles_to_neo4j',
        'schedule': crontab(hour=5, minute=30, day_of_week=0),
    },
    'chainsight-sync-relations-weekly': {
        'task': 'chainsight.tasks.sync_relations_to_neo4j',
        'schedule': crontab(hour=6, minute=0, day_of_week=0),
    },
}
```

## 완료 기준

```
□ CompanyChainProfile ~500건 집약
□ neo4j_synced = False로 설정
□ Celery Beat 9개 스케줄 등록 (동기화 2개는 Phase 3에서 task 구현, heat-score-daily는 CS-4-4에서 구현)
□ celery beat --loglevel=info로 스케줄 확인
```

→ **다음**: cs_31 (Phase 3 시작)

**END OF DOCUMENT**
