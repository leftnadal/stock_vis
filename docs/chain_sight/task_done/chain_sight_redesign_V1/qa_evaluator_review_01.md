# QA Evaluator 검증 보고서 #1

> 브랜치: `data_structure_remodeling_V1`
> 검증일: 2026-04-13
> 대상: Chain Sight 마켓 뷰 PR-1~7 (미커밋)

## 종합 판정: 승인 (조건부)

**종합 점수: 91%**

| 영역 | 점수 | 상태 |
|------|------|------|
| DECISIONS.md 준수 | 95% | 우수 |
| Backend 구조 | 90% | 우수 |
| Migration | 100% | 완벽 |
| Frontend 타입 | 95% | 우수 |
| API 일관성 | 90% | 좋음 |
| 에러 처리 | 85% | 개선 필요 |
| 문서화 | 90% | 우수 |

---

## DECISIONS.md 준수 검증

### neo4j_dirty 플래그 패턴 — 완벽 준수
- `RelationConfidence.neo4j_dirty` 필드 추가 (migration 0005)
- `db_index=True`, `default=True`
- `save()` 시 자동 `neo4j_dirty=True`
- Celery 태스크: neo4j_dirty_sync_tasks.py (weekly, neo4j 큐)

### CUSTOMER_OF 파생 — 완벽 준수
- views.py line 85-87: `derived_type = "CUSTOMER_OF"`
- NeighborGraphView line 458-462: `_display_type()` 함수
- DB 저장 없음

### Undirected 관계 정규화 — 완벽 준수
- neo4j_sync.py: `UNDIRECTED_TYPES` 정의
- `symbol_a < symbol_b` 순서 정규화

### 마켓 뷰 4개 API — 완벽 준수
- seeds, sector/graph, neighbors, signals 모두 구현
- 캐시 TTL: 30분/30분/30분/1시간 (DECISIONS.md 기준 일치)

---

## Backend 검증

### Migration 0005
- dependencies: 0004 → 0005 명확
- 3개 필드: neo4j_dirty, neo4j_synced_at, previous_status
- 인덱스 설정 적절

### Services 패키지화
- services.py → services/ (neo4j_loader, neo4j_sync, seed_selection)
- `__init__.py` re-export로 import 호환성 유지

### Celery 태스크
- seed_selection: 매일 13:00 UTC, max_retries=2
- neo4j_dirty_sync: 매주 일 04:30 UTC, neo4j 큐
- idempotent, exponential backoff 준수

---

## Frontend 검증

### 타입 일치
- frontend/types/chainsight.ts ↔ views.py 응답: 100% 일치
- SeedResponse, SectorGraphResponse, NeighborResponse, SignalFeedResponse 모두 매칭

### 컴포넌트 구현
- 5개 마켓 뷰 컴포넌트 완성
- Zustand store (explorationStore) 정상
- TanStack Query (useMarketView) staleTime 적절

### Date.now() 검사
- 모듈 레벨 사용 없음 (버그 #24 준수)

---

## 비차단 개선 사항 (follow-up)

1. **chainsightService.ts**: fetch() → authAxios 통일 (JWT 일관성)
2. **useInfiniteQuery**: `pageParam as number` → 명시적 타입 정의
3. **RelationCardPanel**: 에러 바운더리 또는 에러 상태 UI 추가
4. **relation_tasks.py**: relation_upgrade/downgrade 판정 로직 완성도 재확인
