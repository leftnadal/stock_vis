# 데이터 무결성 감사 보고서

- 감사 일자: 2026-05-03
- 감사 범위: PostgreSQL FK 정책, CASCADE 체인, Neo4j ↔ PG 동기화, Unique 제약/Race condition
- 방법: 정적 코드 분석 (모델, 마이그레이션, 시그널, Celery 태스크), 코드 수정 없음
- 사전 파악 명령으로 측정한 실측치는 사용자 지시서의 추정치와 일부 차이가 있음(아래 "사전 파악 결과 정정" 참조).

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 비고 |
|--------|------|------|
| 🔴 High | 3 | (1) SET_NULL 후 orphan(`target_company__isnull=True`) 영구 적체, 자동 회수 경로 부재 (2) `RelationConfidence.save()`가 `neo4j_dirty=True`를 무조건 덮어써 동기화 직후 race로 다시 dirty 처리 가능 (3) `chainsight.tasks.sync_tasks.sync_dirty_to_neo4j` 류 multi-batch 작업이 Stock 단일 PK(`symbol`)를 통한 to_field FK에 의존 — 심볼 rename/delete 시 dangling reference 폭발 |
| 🟡 Medium | 5 | (4) `update_or_create` 다발 사용 — 일부 unique 제약 누락/부분 매칭 race 위험 (5) `unique_together` 일관성 부재 (`unique_together` vs `UniqueConstraint` 혼용) (6) `sync_dirty_relations`의 부분 실패 처리 — 일부 실패 시 PG/Neo4j 상태 mismatch (7) `news/models.py`의 `NewsEntity.symbol`은 CharField로 저장되어 `Stock` FK가 아님 (8) `chainsight.tasks.sync_tasks.sync_relations_to_neo4j`의 레거시 정리 분기 — 캐시 키 1년 보존, 멱등성 가정에 의존 |
| 🟢 Low | 4 | (9) AdminActionLog SET_NULL 정책은 감사 추적 의도에 부합 (10) MetricResult.stock = PROTECT — 의도된 가드 (11) BasketItem.clean()의 `pk` 검증 race(낮음) (12) thesis 0003 마이그레이션이 의도적으로 SET_NULL로 변경한 이력 존재 (양호) |

### 사전 파악 결과 정정

지시서의 추정치(SET_NULL 7곳/3파일, CASCADE 37곳/7파일)는 실측과 차이 있음:

| 항목 | 지시서 추정 | 실측 (rg) |
|------|-------------|-----------|
| `on_delete=models.SET_NULL` | 7곳 / 3파일 | **16곳 / 13파일** |
| `on_delete=models.CASCADE` | 37곳 / 7파일 | **88곳 / 21파일** |

추정치만 검토 대상으로 좁히면 SET_NULL 9곳, CASCADE 51곳을 누락하게 됨. 본 보고서는 실측 전체를 기준으로 작성.

---

## FK orphan 위험

### SET_NULL 사용처 (실측 16곳, 13파일)

| 파일 | 줄 | 모델/필드 | 참조 대상 | 의도 추정 | 위험 평가 |
|------|----|-----------|-----------|----------|----------|
| `sec_pipeline/models.py` | 86 | `SupplyChainEvidence.target_company` | `stocks.Stock` | 미상장/외국기업/이름만 매칭된 케이스를 NULL로 보존 | 🔴 High — orphan 누적, 회수 경로는 `signals.py`의 `on_unmatched_resolved`만 (수동 admin 관여 필요) |
| `serverless/models.py` | 660 | `ScreenerAlert.preset` | `ScreenerPreset` | 프리셋 삭제 후 알림은 커스텀 필터로 fallback (`get_effective_filters`) | 🟡 — fallback 로직 있으나 `filters_json`이 비어있으면 알림이 무의미하게 동작 |
| `serverless/models.py` | 808 | `InvestmentThesis.user` | `users.User` | 사용자 삭제 후 공유 테제 보존 | 🟢 — 의도와 일치 |
| `serverless/models.py` | 1409 | `AdminActionLog.user` | `users.User` | 감사 추적 (사용자 삭제돼도 액션 기록 유지) | 🟢 — 의도와 일치 |
| `thesis/models/thesis.py` | 70, 77 | `ThesisAlert.indicator` 등 | `ThesisIndicator`, `ThesisPremise` | 마이그레이션 0003에서 의도적으로 CASCADE→SET_NULL 변경 | 🟢 — 의도된 변경 (이력 명확) |
| `thesis/models/indicator.py` | 15 | `ThesisIndicator.premise` | `ThesisPremise` | 위와 동일 | 🟢 |
| `thesis/models/monitoring.py` | 66 | (FK) | (확인 필요) | 알림 보존 패턴 | 🟢 |
| `macro/models/indicators.py` | 282 | (FK) | macro 지표 | 지표 변경에도 시계열 보존 | 🟢 |
| `portfolio/models.py` | 327 | `AnalysisRun.wallet_snapshot_at_execution` | `WalletSnapshot` | 스냅샷 삭제돼도 분석은 보존 | 🟢 |
| `portfolio/models.py` | 732 | `ChatSession.analysis_run` | `AnalysisRun` | 분석 삭제돼도 대화 보존 | 🟢 |
| `portfolio/models.py` | 831 | `Decision.context_analysis_run` | `AnalysisRun` | 동일 패턴 | 🟢 |
| `chainsight/models/news_event.py` | 54 | self FK | 자기참조 | 동시출현 부모 이벤트 삭제돼도 자식 보존 | 🟡 — self-FK orphan 회수 정책 부재 |
| `rag_analysis/models.py` | 145 | `AnalysisSession.basket` | `DataBasket` | 바구니 삭제돼도 세션 보존 | 🟢 |
| `rag_analysis/models.py` | 256, 263 | `UsageLog.session`, `.message` | `AnalysisSession`, `AnalysisMessage` | 사용량 로그 보존(비용 추적) | 🟢 |

### SET_NULL 후 orphan 정리 로직

> **결론: 자동 회수 메커니즘은 `sec_pipeline/signals.py`의 `on_unmatched_resolved` 단 한 곳에만 존재. 그 외 SET_NULL FK는 NULL 상태로 영구 적체될 수 있음.**

자동 회수 사례:
- `sec_pipeline/signals.py:21-71`
  - `UnmatchedCompanyQueue.status == 'matched'` 시점에 같은 이름·sector 범위 내 `SupplyChainEvidence.target_company__isnull=True`인 레코드를 `update(target_company=target_stock, neo4j_dirty=True)`로 회수.
  - 트리거가 admin/관리자 큐 처리에 의존 — 자동화된 ticker 재매칭은 `sec_pipeline/ticker_matcher.py` (수동 명령 `rematch_unmatched`).

자동 회수 부재 사례 (📌 관찰):
- `chainsight.models.news_event.NewsEvent.parent_event` self-FK SET_NULL — 부모 삭제 시 자식이 떠도는 이벤트로 남음. 회수/삭제 정책 없음.
- `serverless.ScreenerAlert.preset` SET_NULL — `filters_json`이 빈 dict인 알림이 영구 활성 상태로 남을 수 있음. (`is_active=True` + `filters_json={}`이면 의미 없는 매칭)
- `rag_analysis.UsageLog.session/message` SET_NULL — 비용 분석에 의도된 패턴(보존). 대신 시계열이 길어질수록 NULL FK row 비율이 단조 증가. 정리 정책 없음.

### 위험 정도 평가

| 케이스 | 영향 | 권고 |
|--------|------|------|
| `SupplyChainEvidence.target_company` NULL 적체 | `quality_checks.py:91-97`에서 50건 초과 시 alert 발생 → 모니터링은 있음. 하지만 회수는 admin queue 처리 의존. | 🔴 — 자동 batch 재매칭 태스크(`rematch_unmatched`)를 Celery Beat에 등록 검토 |
| `NewsEvent.parent_event` self-FK | 데이터 양이 누적될수록 graph traversal에서 NULL 부모를 만나 분석이 끊김 | 🟡 — 부모 삭제 시 자식 chain 정리 정책 명문화 필요 |
| `ScreenerAlert.preset=NULL` + `filters_json={}` | 알림 무한 발사 또는 무동작 | 🟡 — model `clean()` 또는 `save()`에서 양쪽 모두 비어있을 때 ValidationError |

---

## CASCADE 체인

### 사용처 (실측 88곳, 21파일)

핵심 root는 다음 4개 모델:

1. **`stocks.Stock` (PK = symbol)** — 가장 광범위한 root.
2. **`users.User`** — 사용자 데이터 분리.
3. **`users.Watchlist`** — 사용자별 그래프/관심종목 root.
4. **`portfolio.Portfolio`** — 포트폴리오 분석 root.

### Stock 삭제 시 영향 범위

`stocks.Stock`을 직접 CASCADE/PROTECT/SET_NULL 참조하는 모델 (실측):

| 앱 | 모델 | on_delete | 비고 |
|----|------|-----------|------|
| `users` | `Portfolio.stock` | CASCADE | `to_field='symbol'` |
| `users` | `WatchlistItem.stock` | CASCADE | `to_field='symbol'` |
| `stocks` | `BasePriceData.stock` (Daily/Weekly 등) | CASCADE | `to_field='symbol'`, 시계열 데이터 전부 삭제 |
| `stocks` | `StockOverviewKO.stock` (OneToOne) | CASCADE | `primary_key=True` |
| `stocks` | `EOD signal/news` 류 | CASCADE | 14개 시그널 전부 |
| `validation` | 5개 모델 (BenchmarkDelta, CategoryScore, MetricLatest, NewsSummary, PeerPreset 본/멤버) | CASCADE | 검증 캐시 전체 삭제 |
| `metrics` | `MetricSnapshot`, `IndustryMetricBenchmark`, `PeerMetricBenchmark` | CASCADE | 지표 메타 + 벤치마크 |
| `chainsight` | 8개 모델 (InsiderSignal, RevenueStructure, CapitalDNA, EventReaction, GrowthStage, Sensitivity, NarrativeTag, ChainProfile) | CASCADE | `to_field='symbol', primary_key=True` 패턴 다수 |
| `chainsight` | `NewsEvent.symbol` | **PROTECT** | 의도된 가드 — Stock 삭제 차단 |
| `sec_pipeline` | `RawDocumentStore`, `SupplyChainEvidence.source_company`, `BusinessModelSnapshot` | CASCADE | source는 CASCADE |
| `sec_pipeline` | `SupplyChainEvidence.target_company` | SET_NULL | 위 SET_NULL 섹션 참조 |
| `portfolio` | 4개 모델 (Holding, MetricResult 등) | CASCADE/PROTECT 혼합 | `MetricResult.stock = PROTECT` (의도된 가드) |
| `serverless` | 4개 모델 | CASCADE | screener/llm relation 등 |
| `rag_analysis` | 모델들은 user/basket 통해 간접 연결 | — | Stock 직접 FK 없음 |

> **Stock 1건 삭제 시 영향**: 21개 앱 중 11개 앱의 50+ 테이블이 직간접적으로 row를 잃거나 NULL 처리됨. 단일 Stock 삭제는 **사실상 모든 분석 캐시를 무효화**하는 작업.

### 3단계 이상 연쇄 삭제 시나리오

#### 시나리오 1: User 삭제

```
User
 ├─ CASCADE → Portfolio (users)
 │            ├─ CASCADE → AnalysisRun (portfolio)
 │            │            ├─ CASCADE → MetricResult
 │            │            │              └─ PROTECT → Stock  ⛔ 삭제 차단
 │            │            └─ SET_NULL ← ChatSession.analysis_run
 │            │                          └─ CASCADE → Message
 │            └─ ...
 ├─ CASCADE → Watchlist (users)
 │            ├─ CASCADE → WatchlistItem
 │            └─ CASCADE → CorrelationMatrix (graph_analysis)
 │            └─ CASCADE → CorrelationEdge (graph_analysis)
 │                          └─ CASCADE → CorrelationAnomaly
 ├─ CASCADE → DataBasket (rag_analysis)
 │            └─ CASCADE → BasketItem
 ├─ SET_NULL ← AnalysisSession.user (rag_analysis)
 │            ├─ CASCADE → AnalysisMessage
 │            └─ SET_NULL ← UsageLog
 ├─ CASCADE → UserInterest (users)
 ├─ CASCADE → ScreenerAlert (serverless)
 │            └─ CASCADE → AlertHistory
 ├─ SET_NULL ← InvestmentThesis (serverless)
 ├─ SET_NULL ← AdminActionLog (serverless)
 ├─ CASCADE → ChatSession (portfolio)
 │            └─ CASCADE → Message
 ├─ CASCADE → Decision (portfolio)
 ├─ CASCADE → ThesisCommunity (thesis)
 └─ CASCADE → SavedPath (chainsight)
              └─ CASCADE → SavedPathAction
```

**최대 깊이 5단계** (User → Portfolio → AnalysisRun → MetricResult → … 대화 raw 메시지). MetricResult의 `stock` PROTECT 정책이 Stock 삭제는 막지만 User 삭제 자체는 통과.

#### 시나리오 2: Watchlist 삭제

```
Watchlist
 ├─ CASCADE → WatchlistItem
 ├─ CASCADE → CorrelationMatrix
 ├─ CASCADE → CorrelationEdge
 │            └─ CASCADE → CorrelationAnomaly
 └─ CASCADE → CorrelationAnomaly (직접 FK)
```

WatchlistItem 1개 삭제만으로도 Watchlist 단위로 누적된 거대한 graph_analysis 테이블이 통째로 소실. 백업/스냅샷 정책 없음.

#### 시나리오 3: Portfolio 삭제

```
Portfolio
 └─ CASCADE → AnalysisRun
              ├─ CASCADE → MetricResult
              │              └─ PROTECT ← Stock
              └─ SET_NULL ← ChatSession.analysis_run
                            └─ CASCADE → Message
```

`AnalysisRun.is_finalized` 플래그가 save 차단을 하지만 **delete는 차단하지 않음**. 즉 finalized된 분석도 portfolio 삭제로 유실 가능.

### 위험 평가

| 시나리오 | 위험 | 권고 |
|----------|------|------|
| User 삭제 → 전 영역 데이터 유실 | 🔴 | "soft delete" (is_deleted 플래그) 패턴 검토 또는 사용자 익명화로 전환 |
| Stock 1건 삭제 → 50+ 테이블 영향 | 🔴 | Admin에서 Stock 삭제 차단(superuser only) 또는 PROTECT 우선 검토 |
| Portfolio 삭제 → finalized AnalysisRun까지 유실 | 🟡 | `is_finalized=True`인 run은 PROTECT로 변경 검토 |
| Watchlist 삭제 → 그래프 시계열 유실 | 🟡 | 외부 export/스냅샷 정책 명문화 |

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 사용 현황

#### sec_pipeline (`SupplyChainEvidence`)
- 모델: `sec_pipeline/models.py:99-101` — `neo4j_dirty=True` default, `neo4j_synced_at` 보조.
- 인덱스: `models.Index(fields=['neo4j_dirty'])`.
- 쓰기 트리거:
  - `validator_track_a.py:158` — 신규 evidence 생성 시 dirty=True.
  - `signals.py:52` — orphan 회수 시 dirty=True.
  - `ticker_matcher.py:98-99` — 수동 ticker 매칭 시 dirty=True.
- 동기화 태스크: `sec_pipeline/tasks.py:337-452` (`sync_dirty_to_neo4j`)
  - **2-Phase 구조**: Phase A (PG에서 `select_for_update(skip_locked=True)` 500건 lock+복사) → Phase B (Neo4j DELETE+CREATE) → Phase C (PG dirty=False, synced_at 업데이트).
  - `max_retries=1` — 1회 재시도만 허용.
  - 부분 실패 처리: row별 try/except, 실패 ID는 synced_ids에 미포함 → 다음 batch에서 재시도.
- 모니터링: `quality_checks.py:91-97`이 dirty 적체 50건 초과 시 alert.

#### chainsight (`RelationConfidence`)
- 모델: `chainsight/models/relation_discovery.py:130-135` — `synced_to_neo4j` + `neo4j_dirty` **두 필드 공존**. ⚠️ CLAUDE.md 코딩 규칙 "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용"과 **모순**.
- save() 자동 dirty 세팅: `relation_discovery.py:159-160` — 모든 save()에서 `neo4j_dirty=True` 무조건 덮어씀.
- 동기화 서비스: `chainsight/services/neo4j_sync.py:21-54` (`sync_dirty_relations`)
  - confirmed/probable → upsert, hidden/weak/stale → 삭제.
  - market 관계의 weak는 별도 분기로 보존.
  - PG 업데이트는 `queryset.update()`로 save() 우회 (`# save() 호출 금지 — dirty 다시 True로 덮어씌워짐` 명시).
- 동기화 태스크: `chainsight/tasks/neo4j_dirty_sync_tasks.py:14-19` (`max_retries=2`, `default_retry_delay=60`).
- 보조 sync: `chainsight/tasks/sync_tasks.py:147-176` — 레거시 RELATED_TO 정리 분기 (1년 캐시).

#### chainsight 외 영역
- `news/services/news_neo4j_sync.py` — neo4j 동기화 코드 존재. (확인 필요한 별도 패턴)

### 동기화 실패 시 재시도 메커니즘

| 태스크 | max_retries | retry_delay | 부분 실패 처리 |
|--------|-------------|-------------|----------------|
| `sec_pipeline.sync_dirty_to_neo4j` | 1 | 기본값 | row별 try/except, 미동기화는 dirty=True 유지 (자동 재시도) |
| `chainsight.run_neo4j_dirty_sync` | 2 | 60초 | 위와 동일 패턴, `iterator(chunk_size=100)` |
| `chainsight.sync_relations_to_neo4j` | 1 | 기본값 | 위에 위임 |
| `chainsight.profile sync` | 1 | 기본값 | profile별 try/except |

> **모니터링**: `sec_pipeline/quality_checks.py`의 dirty 적체 50건 alert 외에 chainsight 영역의 적체 모니터링은 발견되지 않음.

### PG ↔ Neo4j 불일치 감지 방법

**현재 구현된 감지 메커니즘**:
1. `neo4j_dirty=True` 카운트 (적체 모니터링) — sec_pipeline만.
2. `quality_checks.py:144` — `evidences.filter(neo4j_dirty=False).count()` 누적 카운트.

**미구현 (위험)**:
- ❌ "PG에는 있고 Neo4j에는 없는" 레코드 reconciliation 작업.
- ❌ "Neo4j에는 있고 PG에는 없는" stale edge 감지.
- ❌ 정기 재동기화(예: 일/주 단위 full sweep). `dirty=True` 트리거가 누락되면 영구 미동기화 가능.
- ❌ `RelationConfidence.synced_to_neo4j` 필드와 `neo4j_dirty` 필드 일관성 검증 — **양쪽 필드가 모순될 수 있음** (예: synced=True + dirty=True).

### 위험 평가

| 항목 | 위험 | 비고 |
|------|------|------|
| `RelationConfidence.save()` 무조건 dirty=True | 🔴 | 동기화 직후 다른 트랜잭션에서 save가 일어나면 무한 dirty 루프. `neo4j_synced_at` 시점 비교 로직 부재 |
| `synced_to_neo4j` + `neo4j_dirty` 두 필드 공존 | 🟡 | CLAUDE.md 규칙 위반, 마이그레이션 0005에서 추가 후 제거 안 됨 |
| Neo4j → PG 역방향 reconciliation 부재 | 🟡 | Neo4j 단독 작성된 edge(레거시 RELATED_TO 등) 감지가 cache flag 의존 |
| 부분 실패 시 PG/Neo4j 상태 mismatch | 🟢 | dirty 유지로 자동 재시도 — 설계상 양호 |
| chainsight dirty 적체 모니터링 부재 | 🟡 | sec_pipeline에는 있음 — 동일 alert를 chainsight에도 추가 필요 |

---

## Unique 제약조건

### `unique_together` / `UniqueConstraint` 사용 현황

> 일관성 부재: `unique_together`(legacy)와 `models.UniqueConstraint`(권장)가 혼용됨. Django 4+에서는 `UniqueConstraint`가 표준.

#### `unique_together` 사용처 (대부분)
- `stocks/models.py`: `(stock, date)` — DailyPrice/WeeklyPrice/MonthlyPrice; `(stock, period_type, fiscal_year, fiscal_quarter)` — 재무제표 3종; `(stock, signal_date, signal_tag)` — 신호 카드.
- `users/models.py`: `(user, stock)`, `(user, name)` (Watchlist), `(watchlist, stock)`, `(user, interest_type, value)`.
- `serverless/models.py`: 11개 (date+symbol 조합 다수).
- `chainsight/models/relation_discovery.py`: `(symbol_a, symbol_b)`, `(symbol_a, symbol_b, period)`, `(symbol_a, symbol_b, relation_type)`.
- `validation/models/`: 5종 (preset_key, fiscal_year 포함 4-tuple 등).
- `metrics/models/`: `(symbol, fiscal_year, metric_code, preset_key)`.
- `news/models.py`: `(news, symbol)`, `(symbol, date)`.
- `thesis/models/`: 4종 (snapshot/keyword/community/indicator).
- `macro/models/`: 4종.
- `graph_analysis/models.py`: 4종 (watchlist + date 조합).
- `sec_pipeline/models.py`: `(alias, context_sector)`.

#### `models.UniqueConstraint` 사용처 (소수)
- `portfolio/migrations/0001_initial.py`:
  - `('metric_id', 'industry_code', 'date')` — `unique_percentile_cache`.
  - `('analysis_run', 'priority')` — `unique_card_priority_per_run`.
  - `('analysis_run', 'stock', 'metric_id')` — `unique_comment_per_run_stock_metric`, `unique_metric_result_per_run_stock`.
  - `(wallet, stock)` — wallet holding.

### `update_or_create` / `get_or_create` 사용 현황

총 150건, 68파일. 핵심 부하 영역:

| 파일 | 횟수 | 호출 위치 |
|------|------|-----------|
| `api_request/stock_service.py` | 8 | Stock 동기화 메인 루프 |
| `portfolio/tests/fixtures/sample_wallet.py` | 6 | 테스트 |
| `serverless/services/keyword_service.py` 외 keyword_*.py | 1~3 각각 | 키워드 캐시 |
| `chainsight/tasks/relation_tasks.py` | 6 | RelationConfidence 갱신 |
| `tests/serverless/test_supply_chain_service.py` | 6 | 테스트 |
| `tests/unit/thesis/test_quarterly_metric_fetcher.py` | 6 | 테스트 |

### Race condition 가능성

`update_or_create`는 Django가 내부적으로 `select → update_or_insert`를 lock 없이 수행하므로 **동시 실행 시 IntegrityError 또는 중복 row** 발생 가능. 안전한 패턴:
- ✅ unique 제약이 있는 필드 조합으로 `lookups` 호출
- ❌ unique 제약이 없는 부분 lookup, 또는 `defaults`에 비결정적 값

#### 검출된 race 위험 케이스

1. **`sec_pipeline/tasks.py:281-330` (`seed_relations_to_chainsight`)**
   - `RelationConfidence`의 unique는 `(symbol_a, symbol_b, relation_type)`.
   - sec_pipeline에서 동일 evidence를 batch 처리 중 동일 페어가 동시에 update_or_create되면 race 가능.
   - 완화책: Phase A에서 `select_for_update(skip_locked=True)` 사용 — sec_pipeline 자체는 안전.
   - **위험**: chainsight 영역의 다른 source가 같은 RelationConfidence를 업데이트하면 PROVIDER 간 race 발생 가능. lock 없음.

2. **`chainsight/tasks/relation_tasks.py` (6 호출)**
   - RelationConfidence를 다양한 source(news/price/peer 등)에서 update_or_create.
   - source별로 별개 Celery 태스크 → 동일 페어 동시 처리 가능.
   - `RelationConfidence.save()`가 `previous_status` 추적을 위해 DB read 후 write — read와 write 사이 lost update 가능.

3. **`stocks/services/stock_sync_service.py` (2 호출)**
   - Stock 단일 PK upsert — race 시 양쪽 모두 IntegrityError 없이 통과 가능 (PK가 unique).
   - 단, 동시 호출 시 `last_updated`가 비결정적으로 결정됨 — 데이터 정확성에는 영향 없음.

4. **`news/services/aggregator.py` (2 호출)**
   - `NewsEntity.unique_together = ('news', 'symbol')` 보장 → race 시 IntegrityError로 실패 (재시도 의존).

5. **`serverless/services/keyword_service.py` 등**
   - 키워드 unique 제약 보장 → race 시 IntegrityError 발생 가능. 재시도 메커니즘 없음.

### Unique 제약 누락/이상 케이스

| 모델 | 현황 | 평가 |
|------|------|------|
| `news/models.NewsEntity` | `(news, symbol)` 만. (entity_type, exchange) 등 메타가 다른 동일 symbol은 중복 허용 | 🟢 — 의도와 일치 |
| `chainsight/models/relation_discovery.PriceCoMovement` | `(symbol_a, symbol_b, period)` | 🟢 |
| `chainsight/models/relation_discovery.CoMentionEdge` | `(symbol_a, symbol_b)` | 🟡 — 방향성 정규화(`normalize_pair`) 의존. 코드 외부에서 raw insert 시 (a,b)/(b,a) 중복 가능 |
| `chainsight/models/relation_discovery.RelationConfidence` | `(symbol_a, symbol_b, relation_type)` | 🟡 — 위와 동일. UNDIRECTED_TYPES 정규화는 `services/neo4j_sync.py`에만 존재, ORM 레벨 가드 없음 |
| `validation` preset_key 포함 unique 4종 | 명시적 4-tuple unique | 🟢 |
| `serverless.LLMExtractedRelation` | `(source_symbol, target_symbol, relation_type, source_id)` (마이그레이션 0011) | 🟢 |
| `portfolio.AnalysisRun` | `(analysis_run, stock, metric_id)` UniqueConstraint | 🟢 |

---

## 부록: 사전 파악 명령 결과

```
on_delete=models.SET_NULL → 16곳 (13파일)
on_delete=models.CASCADE → 88곳 (21파일)
unique_together / UniqueConstraint → 100곳+ (Glob 결과 기준 truncated)
update_or_create / get_or_create → 150건 (68파일)
neo4j_dirty 참조 → 35곳 (sec_pipeline 18곳, chainsight 17곳)
```

핵심 모델 파일 18개:
```
graph_analysis/models.py
users/models.py
news/models.py
stocks/models.py
serverless/models.py
sec_pipeline/models.py
portfolio/models.py
rag_analysis/models.py
chainsight/models/* (10+ 파일)
thesis/models/* (5 파일)
macro/models/* (3 파일)
metrics/models/* (3 파일)
validation/models/* (5 파일)
```

---

## 권고 우선순위 (요약)

1. 🔴 `RelationConfidence.save()`의 `neo4j_dirty=True` 무조건 덮어쓰기 — 동기화 직후 race 가능. `neo4j_synced_at` 비교 또는 `update_fields` exclude 도입.
2. 🔴 `SupplyChainEvidence.target_company` orphan 자동 회수 — `rematch_unmatched`를 Beat 등록 검토.
3. 🔴 Stock/User 삭제 가드 — admin 권한 또는 PROTECT 변경 검토.
4. 🟡 `RelationConfidence.synced_to_neo4j` 필드 제거 (CLAUDE.md 규칙 위반).
5. 🟡 chainsight Neo4j dirty 적체 모니터링 alert 추가 (sec_pipeline 패턴 참고).
6. 🟡 PG ↔ Neo4j 정기 reconciliation 작업 도입 (주 1회 full sweep).
7. 🟡 `unique_together` → `UniqueConstraint` 점진 마이그레이션.
8. 🟡 `ScreenerAlert.preset=NULL && filters_json={}` 검증 추가.
