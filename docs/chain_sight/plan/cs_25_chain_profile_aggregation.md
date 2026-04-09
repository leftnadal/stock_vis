# CS-2-5: CompanyChainProfile 집약 + Celery Beat 등록

> **작업 번호**: CS-2-5
> **목표**: 개별 프로파일 → ChainProfile 집약 + Celery Beat 스케줄 전체 등록
> **예상 소요**: 1일
> **선행 조건**: CS-2-1~CS-2-4 완료
> **산출물**: `chainsight/tasks/sync_tasks.py`, Celery Beat 설정

---

## 집약 로직

```python
@shared_task
def aggregate_chain_profiles():
    """Celery Beat: 주 1회 (일요일 05:00)"""
    # GrowthStage → growth_stage, growth_confidence
    # CapitalDNA → buyback/dividend/capex/ma_tendency
    # SensitivityProfile (있으면) → interest_rate/forex/commodity/regulation_sensitivity
    # validation/CategorySignal (서비스 레이어) → score_profitability, score_growth ...
    # neo4j_synced = False (CS-3-1에서 동기화)
```

## ⚠️ 점검 결과 반영: Celery Beat 스케줄 등록

이전 작업 지시서에서 누락된 Celery Beat 설정을 이 작업에서 등록한다.

```python
# config/settings.py (또는 config/celery.py) CELERY_BEAT_SCHEDULE에 추가

CELERY_BEAT_SCHEDULE = {
    # === Chain Sight — 일간 ===
    'chainsight-co-mention-daily': {
        'task': 'chainsight.tasks.relation_tasks.extract_co_mentions',
        'schedule': crontab(hour=6, minute=30),
    },
    # === Chain Sight — 주간 (일요일) ===
    'chainsight-profiles-weekly': {
        'task': 'chainsight.tasks.profile_tasks.calculate_all_profiles',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
    },
    'chainsight-price-comovement-weekly': {
        'task': 'chainsight.tasks.relation_tasks.calculate_price_co_movement',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    'chainsight-relation-confidence-weekly': {
        'task': 'chainsight.tasks.relation_tasks.update_relation_confidence',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
    },
    'chainsight-stale-decay-weekly': {
        'task': 'chainsight.tasks.relation_tasks.check_stale_and_decay',
        'schedule': crontab(hour=4, minute=30, day_of_week=0),
    },
    'chainsight-chain-profile-weekly': {
        'task': 'chainsight.tasks.sync_tasks.aggregate_chain_profiles',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),
    },
    # === Chain Sight — 주간 동기화 (Phase 3 완료 후 활성화) ===
    'chainsight-sync-profiles-weekly': {
        'task': 'chainsight.tasks.sync_tasks.sync_profiles_to_neo4j',
        'schedule': crontab(hour=5, minute=30, day_of_week=0),
    },
    'chainsight-sync-relations-weekly': {
        'task': 'chainsight.tasks.sync_tasks.sync_relations_to_neo4j',
        'schedule': crontab(hour=6, minute=0, day_of_week=0),
    },
}
```

⚠️ Phase 3 동기화 task(sync_profiles, sync_relations)는 Phase 3 완료 전까지 주석 처리하거나, task 자체가 데이터 없으면 no-op으로 동작하게 구현.

## 완료 기준

```
□ CompanyChainProfile 적재 (~500건)
□ neo4j_synced = False 설정
□ Celery Beat 스케줄 8개 등록 (일간 1 + 주간 5 + 동기화 2)
□ celery beat 구동 시 스케줄 로그 확인

★ M2 달성: "관계 신뢰도 엔진 작동"
```

→ **다음**: cs_31

**END OF DOCUMENT**
