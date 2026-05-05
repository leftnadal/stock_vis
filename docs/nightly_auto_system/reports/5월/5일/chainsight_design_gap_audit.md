# Chain Sight 설계 갭 감사

**감사일**: 2026-05-06
**대상**: `docs/chain_sight/plan/` 설계 문서 vs `chainsight/` 백엔드 + `frontend/components/chainsight/` 프론트엔드 구현
**기준**: 읽기 전용 감사 (코드 수정 없음)

---

## 1. 요약 (구현률)

### 전체 구현률

| 영역 | 구현률 | 평가 |
|------|--------|------|
| **Phase 0~4 백엔드 (cs_00 ~ cs_43)** | **약 87%** | 핵심 데이터 파이프라인 + REST API 완성. GDS task 미구현, 일부 응답 필드 누락 |
| **Phase 5 프론트엔드 (cs_5x)** | **약 80%** | redesign_v1으로 일부 대체. cs_54 완전 구현, cs_51~53은 Deep Dive로 진화 |
| **Redesign v1 (현재 활성 설계)** | **약 95%** | 시드/API/UI 핵심 완성. 애니메이션 + 일부 응답 필드 미구현 |
| **종합** | **약 90%** | 운영 가능 수준. 미구현 항목은 대부분 cosmetic 또는 future scope |

### 설계 문서 계층 (중요)

```
cs_51~54 + cs_5_frontend_design_v2  (2026-04-04, 폐기/대체)
              ↓
redesign_v1_260409  (2026-04-10, 현재 활성)  ← 신규 작업 시 이 문서 기준
```

- **`cs_5_frontend_design_v2.md` → (D) 폐기/대체**: redesign_v1이 마켓 뷰(`/chainsight`) + Deep Dive(`/chainsight/[symbol]`)로 분리하는 새 아키텍처 도입
- **`cs_51~54` → 부분 흡수**: Deep Dive 워크스페이스로 진화 (폐기 아님, 용도 변경)
- **백엔드 cs_* 문서**: redesign_v1과 호환, 폐기되지 않음

### 산출 데이터 규모 (task_done 기록 기준)

- :Stock 532개, :Sector 17개, :Industry 128개
- PEER_OF 8,350개, RelationConfidence 3,527개
- PriceCoMovement 2,473쌍, CoMentionEdge 744쌍
- GrowthStage 480개, CapitalDNA 473개

---

## 2. 문서별 상태 테이블

### 2.1 백엔드 cs_* 문서 (Phase 0~4)

| 문서 | 핵심 항목 | 상태 | 코드 위치 / 미구현 항목 | 비고 |
|------|---------|------|---------------------|------|
| **cs_00** | 레거시 정리, API 테스트 5개 | (B) 부분 | serverless 정리 완료. `decisions/003_api_access_test.md` 미작성 | API 테스트 결과 미기록 |
| **cs_01** | 12개 테이블 migrations | (A) 완전 | `chainsight/migrations/0001~0007` | ✅ |
| **cs_02** | Neo4j 드라이버 + PID fork 안전 | (A) 완전 | `chainsight/graph/repository.py` | ✅ Lazy init |
| **cs_03** | Constraint 4 + Index 2 | (A) 완전 | `chainsight/graph/schema.py`, `init_neo4j_schema` 명령 | ✅ |
| **cs_11** | Stock 노드 ~500개 | (A) 완전 | `management/commands/load_stocks_to_neo4j.py` | 532개 ✅ |
| **cs_12** | Sector/Industry 로드 | (A) 완전 | `management/commands/load_sectors_to_neo4j.py` | 17+128개 ✅ |
| **cs_13** | PEER_OF 관계 | (A) 완전 | `tasks/peer_tasks.py`, `management/commands/load_peers_to_neo4j.py` | 8,350개 ✅ |
| **cs_21** | GrowthStage + CapitalDNA | (A) 완전 | `tasks/profile_tasks.py` | 480/473개 ✅ |
| **cs_21b** | Sensitivity (FMP) | (A) 완전 | `tasks/sensitivity_tasks.py` | ✅ |
| **cs_21c** | InsiderSignal (Finnhub) | (A) 완전 | `tasks/insider_tasks.py` | ✅ |
| **cs_22** | CoMention 추출 | (A) 완전 | `tasks/relation_tasks.py: extract_co_mentions` | 744쌍 ✅ |
| **cs_23** | PriceCoMovement (90일 corr) | (A) 완전 | `tasks/relation_tasks.py: calculate_price_co_movement` | 2,473쌍. 단, 설계는 "같은 섹터 내" / 구현은 "PEER_OF 관계 내" — **범위 다름** |
| **cs_24** | RelationConfidence 5단계 | (A) 완전 | `tasks/relation_tasks.py: update_relation_confidence` | 3,527개 ✅ |
| **cs_25** | ChainProfile 집약 | (A) 완전 | `tasks/sync_tasks.py: aggregate_chain_profiles` | ✅ |
| **cs_31** | Profile Neo4j 동기화 | (A) 완전 | `tasks/sync_tasks.py: sync_profiles_to_neo4j` | Delta sync ✅ |
| **cs_32** | Relation Neo4j 동기화 | (A) 완전 | `tasks/sync_tasks.py: sync_relations_to_neo4j` + `services/neo4j_sync.py` | Dirty sync 추가 구현 ✅ |
| **cs_33** | GDS (PageRank/Louvain/Betweenness) 배치 | **(D) 폐기/대체** | Neo4j 직접 쿼리로 실행 (Celery task 없음). 결과는 노드 속성으로 저장됨. `path_service.py`에서 `pagerank_score` 읽기 가능 | 자동화 안 됨 — 수동 실행 |
| **cs_41** | Graph API | (B) 부분 | `api/views.py: ChainSightGraphView` | `explanation` 필드 미포함 (basis_summary 누락) |
| **cs_42** | Suggestion API | (A) 완전 | `api/views.py: ChainSightSuggestionView` | 5개 카테고리 ✅ |
| **cs_43** | Trace API | (A) 완전 | `api/views.py: ChainSightTraceView` | shortestPath ✅ |
| **relation_confidence_design_v1** | Tier 시스템, 5단계, 템플릿 | (A) 완전 | `tasks/relation_tasks.py` | 정책표 100% ✅ |
| **chain_sight_roadmap_v1.3** | M0~M4 마일스톤 | (A) 거의 완전 | M0~M4 달성 | GDS 자동화만 미흡 |

### 2.2 프론트엔드 cs_5x 문서 (Phase 5)

| 문서 | 핵심 항목 | 상태 | 코드 위치 / 비고 |
|------|---------|------|----------------|
| **cs_51** Spotlight 그래프 | Lazy expansion | (B) 부분 | `GraphCanvas.tsx` (Deep Dive에 구현). 마켓 뷰는 redesign_v1 `MarketGraphCanvas.tsx` |
| **cs_52** AI Guide UI | 카테고리 카드 | (B) 부분 | `AIGuidePanel.tsx` (Deep Dive). 마켓 뷰의 `RelationCardPanel`이 유사 역할 |
| **cs_53** Chain Trace UI | From/To 경로 | (B) 부분 | `TracePathView.tsx` (Deep Dive only). 마켓 뷰 트레일은 별개 컨셉 |
| **cs_54** 종목상세 연계 | 미니 그래프 + 딥링크 | **(A) 완전** | `app/stocks/[symbol]?tab=chain-sight` + `GraphMiniView.tsx` + `/chainsight?focus={symbol}` 딥링크 ✅ |
| **cs_5_frontend_design_v2** | 통합 워크스페이스 | **(D) 폐기/대체** | redesign_v1으로 완전 대체 |

### 2.3 Redesign v1 (현재 활성)

| 문서 | 핵심 항목 | 상태 | 코드 위치 / 미구현 |
|------|---------|------|----------------|
| **chainsight_seed_node_design** | 5개 시드 소스 + 합산/랭킹 + 캐싱 | (A) 완전 | `services/seed_selection.py` 전체 + `tasks/seed_tasks.py` ✅ |
| **chainsight_api_design (4개 API)** | seeds/sector_graph/neighbors/signals | (B) 부분 | `api/views.py` — `signal_count` 누락 (seeds, neighbors), `center.volume_ratio` 누락, `evidence_tier_best` 필드명 상이 |
| **chainsight_ui_ux_design** | 5개 영역 + 상태 관리 + 애니메이션 | (B) 부분 | 5개 컴포넌트 + Zustand 모두 구현. 애니메이션 3종 미구현 (bounce / 중심이동 / 자동스크롤). Chain path highlight 미구현 |
| **chainsight_marketview_pr_prompts** | PR-1 ~ PR-7 | (A) 완전 | `task_done/chain_sight_redesign_V1/PR-1~7` 모두 보고서 존재 ✅ |
| **PR-1 schema migration** | 0005, 0006, 0007 마이그레이션 | (A) 완전 | `migrations/0005_*`, `0006_*`, `0007_*` ✅ |
| **PR-2 seed selection task** | Celery Beat 13:00 UTC | (A) 완전 | `config/celery.py`에 등록 ✅ |
| **PR-3 neo4j dirty sync** | dirty 플래그 패턴 | (A) 완전 | `services/neo4j_sync.py: sync_dirty_relations` ✅ |
| **PR-4 market view API** | 4개 엔드포인트 | (B) 부분 | 위 chainsight_api_design 항목 참조 |
| **PR-5 FE core UI** | 5개 컴포넌트 + 라우팅 | (A) 완전 | `app/chainsight/page.tsx` ✅ |
| **PR-6 trail and cards** | ExplorationTrail + RelationCardPanel | (A) 완전 | 컴포넌트 구현 ✅ (자동 스크롤만 미흡) |
| **PR-7 chain story feed** | 무한 스크롤 | (A) 완전 | `ChainStoryFeed.tsx` ✅ |
| **data_quality_3_fixes** | 3대 이슈 수정 | (A) 완전 | 섹터 수익률, 관계 타입 다양화, trigger_summary 번역 모두 적용 ✅ |

---

## 3. 미구현 항목 상세

### 3.1 Blocking (설계서 명시 필드 누락)

#### B-1. `signal_count` 필드 누락 (HIGH)

- **설계서**: `chainsight_seed_node_design.md §2.3`, `chainsight_api_design.md §2, §4`
- **요구**: seeds[] 및 neighbors[] 응답에 `signal_count: int` (시드 소스 출현 횟수) 포함
- **현재**: `seed_selection.py:331`에서 계산은 됨(`len(reasons)`)이나 `cache_seed_result()` (라인 396-424)에서 직렬화 시 누락
- **영향**: 프론트엔드의 시드 카드 "signal badge" 우선순위 표시 불가. 클라이언트 workaround(`seed_reasons.length`)는 가능하나 서버 계약 위반

#### B-2. `center.volume_ratio` 필드 누락 (MEDIUM)

- **설계서**: `chainsight_ui_ux_design.md §9.3` (`why now` 조합에 daily_return + volume_ratio 사용)
- **현재**: `api/views.py:478-488` (NeighborGraphView)의 center dict에 volume_ratio 없음
- **영향**: 중심 노드의 "왜 지금" 메시지 일관성 부족

#### B-3. `evidence_tier_best` 필드명 불일치 (LOW)

- **설계서**: `chainsight_api_design.md §4` — `evidence_tier_best`
- **현재**: `evidence_tier`로 응답
- **영향**: 명세서-구현 불일치

#### B-4. `cs_41` Graph API의 `explanation` 필드 누락 (LOW)

- **설계서**: `cs_41_graph_api.md` — edges에 `explanation` 필드 (relation_basis_summary 매핑)
- **현재**: market_signals 구조는 정확하나 explanation 필드 미포함
- **영향**: 그래프 노드 상세 패널의 관계 설명 텍스트 부재

### 3.2 Non-blocking (애니메이션 / Cosmetic)

#### N-1. 시드 노드 Bounce 애니메이션 미구현
- **설계서**: `chainsight_ui_ux_design.md §7`
- **위치**: `MarketGraphCanvas.tsx`

#### N-2. 중심 이동 애니메이션 (300ms) 미구현
- **설계서**: `chainsight_ui_ux_design.md §7` (이전 중심 → 왼쪽 / 새 중심 → 중앙 / 새 이웃 페이드 인)
- **위치**: `MarketGraphCanvas.tsx`
- **현재**: 즉시 재렌더링

#### N-3. 트레일 자동 스크롤 미구현
- **설계서**: `chainsight_ui_ux_design.md §8` (300ms 오른쪽 스크롤)
- **위치**: `ExplorationTrail.tsx`

#### N-4. Chain path highlight 미구현
- **설계서**: `chainsight_ui_ux_design.md §10` (stroke-width 3px + drop-shadow)
- **현재**: `explorationStore.highlightedChain` 상태는 저장되고 클릭 핸들러도 작동하나 `MarketGraphCanvas.tsx`에서 렌더링에 반영 안 됨

### 3.3 자동화 미흡

#### Z-1. GDS 알고리즘 Celery task 부재 (cs_33)
- **설계서**: `cs_33_gds_algorithms.md` — PageRank, Louvain, Betweenness를 주 1회 배치
- **현재**: Neo4j 콘솔에서 수동 `gds.pageRank.write()` 호출. 결과는 노드 속성으로 저장됨
- **갭**: 정기 갱신 없음, 모니터링/로깅 부재
- **권장**: `chainsight/tasks/gds_tasks.py` 신설 + Celery Beat 등록

#### Z-2. cs_00 API 테스트 결과 미기록
- **설계서**: `cs_00_legacy_cleanup_api_test.md` — 5개 API 접근성 테스트 후 `decisions/003_api_access_test.md` 작성
- **현재**: 결과 문서 없음

#### Z-3. 성능 메트릭 로깅 부재
- **설계서**: `chainsight_api_design.md §4` — neighbors API p95 < 200ms 목표
- **현재**: ChainSightGraphView만 응답 시간 측정, 그 외 미측정. 응답 헤더 `X-Query-Ms` 없음

### 3.4 부록: 설계 미기록 추가 구현 (참고)

설계서에 없으나 코드에 존재 — 운영 가치 있음, 갭 아님:

- **`services/neo4j_sync.py` Dirty Sync 패턴**: cs_32 단순 MERGE 설계를 초과하여 dirty flag 기반 delta sync, 동적 relation_type, 레거시 RELATED_TO 정리 포함
- **추가 API 엔드포인트**: SeedListView, SectorGraphView, NeighborGraphView, SignalFeedView, WatchlistViewSet — redesign_v1과 호환되는 마켓 뷰 확장
- **ChainNewsEvent 모델**: cs_22 언급만 있던 것을 완전 구현 (source, source_id, symbols, published_at)

---

## 4. 폐기/대체 항목

### 4.1 (D) 완전 폐기/대체

| 문서 | 대체된 곳 | 사유 |
|------|---------|------|
| **`cs_5_frontend_design_v2.md`** | `redesign_v1_260409/chainsight_ui_ux_design.md` | 단일 워크스페이스 → 마켓 뷰 + Deep Dive 분리 아키텍처로 재설계 (2026-04-10) |
| **`cs_33_gds_algorithms.md`의 Celery task 구조** | Neo4j 직접 쿼리 실행 | 결과(pagerank_score, community_id 노드 속성)는 동일하나 자동화 방식 변경 (자동화는 안 됨) |

### 4.2 (B) 용도 변경 (폐기 아님 — 재해석)

`cs_51` ~ `cs_54`는 폐기되지 않음. redesign_v1에서 **Deep Dive 워크스페이스(`/chainsight/[symbol]`)** 의 일부로 흡수됨.

| 원안 | 현재 위치 |
|------|---------|
| **cs_51 (Spotlight 그래프)** | Deep Dive 메인 그래프 (`GraphCanvas.tsx`) |
| **cs_52 (AI Guide UI)** | Deep Dive 좌측 패널 (`AIGuidePanel.tsx`) |
| **cs_53 (Chain Trace UI)** | Deep Dive 하단 (`TracePathView.tsx`). 마켓 뷰의 `ExplorationTrail`은 다른 컨셉(네비게이션 로그) |
| **cs_54 (종목상세 연계)** | 그대로 유지 + 개선. 진입점이 `/chainsight/[symbol]` 직접 → `/chainsight?focus={symbol}` 딥링크로 변경 (마켓 뷰 우선 노출) |

### 4.3 모델/스키마 진화

| 원안 | 현재 |
|------|------|
| `RelationDiscovery` (legacy) | `RelationConfidence` v2.1 (24개 필드, 5단계 상태)로 완전 재구현 |
| `cs_23` "같은 섹터 내" 가격 상관 | "PEER_OF 관계 내"로 범위 변경 (산출 2,473쌍 정상 작동) |

---

## 부록: 권장 조치 우선순위

| 순위 | 항목 | 위치 | 비용 |
|------|------|------|------|
| 1 (HIGH) | `signal_count` 필드 추가 (seeds/neighbors) | `services/seed_selection.py:396-424` | S |
| 2 (HIGH) | Celery Beat 8개 task 등록 검증 | `config/celery.py` | S |
| 3 (MED) | `center.volume_ratio` 추가 | `api/views.py:478-488` | XS |
| 4 (MED) | GDS task 자동화 (`gds_tasks.py` 신설) | 신규 파일 | M |
| 5 (MED) | Chain path highlight 렌더링 | `MarketGraphCanvas.tsx` | S |
| 6 (LOW) | 애니메이션 3종 (bounce/transition/auto-scroll) | FE 컴포넌트 3개 | M |
| 7 (LOW) | `evidence_tier_best` 필드명 정규화 | `api/views.py:512,566` | XS |
| 8 (LOW) | `cs_41` `explanation` 필드 추가 | `ChainSightGraphView` | XS |
| 9 (LOW) | `decisions/003_api_access_test.md` 작성 | 신규 문서 | XS |
| 10 (LOW) | 설계 문서 버전 정리 (cs_* 현재 상태 반영) | `docs/chain_sight/plan/` | M |

**범례**: XS = <1h, S = 1~4h, M = 0.5~2d
