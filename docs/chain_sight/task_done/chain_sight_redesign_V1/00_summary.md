# Chain Sight 마켓 뷰 Redesign V1 — 전체 요약

> **완료일**: 2026-04-10
> **브랜치**: `data_structure_remodeling_V1`
> **설계서**: `docs/chain_sight/plan/redesign_v1_260409/`

## PR 의존성 그래프

```
PR-1 스키마 마이그레이션 (보완 완료)
 ├─→ PR-2 시드 선정 Task ✅
 │    └─→ PR-4 API 4종 ✅
 │         ├─→ PR-5 FE: 상태 + 섹터바 + 그래프 ✅
 │         │    ├─→ PR-6 FE: 트레일 + 관계 카드 ✅
 │         │    └─→ PR-7 FE: 체인 스토리 피드 ✅
 └─→ PR-3 Neo4j Sync 개선 ✅
```

## 파일 변경 요약

### 백엔드 (신규 7 + 수정 4)

| 구분 | 파일 |
|------|------|
| **신규** | `chainsight/services/__init__.py` |
| **이동** | `chainsight/services/neo4j_loader.py` (← services.py) |
| **신규** | `chainsight/services/seed_selection.py` |
| **신규** | `chainsight/services/neo4j_sync.py` |
| **신규** | `chainsight/tasks/seed_tasks.py` |
| **신규** | `chainsight/tasks/neo4j_dirty_sync_tasks.py` |
| **신규** | `chainsight/migrations/0005_add_neo4j_dirty_previous_status.py` |
| **수정** | `chainsight/models/relation_discovery.py` |
| **수정** | `chainsight/utils.py` |
| **수정** | `chainsight/api/views.py` |
| **수정** | `chainsight/api/urls.py` |
| **수정** | `config/celery.py` |

### 프론트엔드 (신규 7 + 수정 4)

| 구분 | 파일 |
|------|------|
| **신규** | `frontend/lib/stores/explorationStore.ts` |
| **신규** | `frontend/hooks/useMarketView.ts` |
| **신규** | `frontend/components/chainsight/SectorBar.tsx` |
| **신규** | `frontend/components/chainsight/MarketGraphCanvas.tsx` |
| **신규** | `frontend/components/chainsight/ExplorationTrail.tsx` |
| **신규** | `frontend/components/chainsight/RelationCardPanel.tsx` |
| **신규** | `frontend/components/chainsight/ChainStoryFeed.tsx` |
| **신규** | `frontend/app/chainsight/page.tsx` |
| **수정** | `frontend/types/chainsight.ts` |
| **수정** | `frontend/services/chainsightService.ts` |
| **수정** | `frontend/components/layout/Header.tsx` |
| **수정** | `frontend/app/stocks/[symbol]/page.tsx` |

## 마켓 뷰 5개 컴포넌트

```
/chainsight 페이지
├── ① SectorBar          — 섹터 버튼 바 (seed_count DESC)
├── ② MarketGraphCanvas  — 그래프 캔버스 (overview/neighbor 분기)
├── ③ ExplorationTrail   — 탐색 트레일 (가로 스크롤 + undo)
├── ④ RelationCardPanel  — 관계 카드 (pre-focus/focused 분기)
└── ⑤ ChainStoryFeed     — 체인 스토리 (글로벌 chain flow)
```

## API 엔드포인트 4종

| 경로 | 용도 |
|------|------|
| `GET /chainsight/seeds/` | 오늘의 시드 + 섹터 요약 |
| `GET /chainsight/sector/{sector}/graph/` | 섹터 overview graph |
| `GET /chainsight/{symbol}/neighbors/` | 중심 이동 + 관계 카드 |
| `GET /chainsight/signals/` | 글로벌 체인 시그널 |

## Celery Beat 추가

| 태스크 | 스케줄 |
|--------|--------|
| `chainsight-seed-selection` | 매일 13:00 UTC |
| `chainsight-neo4j-dirty-sync` | 매주 일 04:30 UTC (neo4j queue) |

## 타입 검증

- TypeScript `tsc --noEmit`: 새 파일 에러 0건
- Django import 검증: 모든 신규 모듈 import 성공

## 범위 밖 (후속 작업)

- Heat Score 계산 (Phase 2 task)
- 전환 애니메이션 (300ms ease-out, bounce)
- LLM 기반 chain title/summary 생성
- 2차 카드 설명 (relation_summary, why_now, insight_summary)
- 모바일 대응
- Graph Data Science (PageRank, Louvain)
