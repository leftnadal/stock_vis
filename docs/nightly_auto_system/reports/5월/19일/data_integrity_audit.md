# 데이터 무결성 감사 보고서

- 작성일: 2026-05-19
- 범위: Backend 전체 (`*/models*.py`, `*/tasks*.py`, `*/services/*.py`, `*/signals.py`)
- 모드: read-only (코드 수정 없음)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 영역 |
|--------|------|----------|
| 🔴 HIGH | 3 | (1) Stock FK 32곳 중 27곳이 CASCADE → 종목 1건 삭제로 10여 개 도메인 동시 멸실 / (2) chainsight Neo4j sync에 quality_checks 부재 (sec_pipeline 만 있음) / (3) `update_or_create` 124곳 중 다수가 `transaction.atomic` 미사용 → unique 제약 race condition 시 IntegrityError 산발 |
| 🟡 MEDIUM | 4 | (1) SET_NULL 17곳 모두 orphan 자동 cleanup 없음 (수동 rematch 명령 1개만 존재: sec_pipeline) / (2) RawDocumentStore CASCADE 체인 (Stock → SupplyChainEvidence → 옆가지) 3단 / (3) graph_analysis CASCADE 8건 자기참조 / (4) `unique_together` 28건은 사용되지만 `UniqueConstraint`는 portfolio 4건만 — 신모델 마이그레이션 비일관 |
| 🟢 LOW | 3 | (1) Neo4j dirty 플래그 패턴 통일 완료(audit P0 #9) / (2) PROTECT 7건 — 의도된 차단(MetricDefinition, RoleAssignment, AnalysisRun 등) / (3) SET_NULL 사용은 audit 추적 모델(AdminActionLog, UsageLog)에 적절히 배치 |

**총계**: HIGH 3 · MEDIUM 4 · LOW 3

### 검색 통계 (실제 카운트)

| 항목 | 사용자 보고 | 실측 |
|------|------------|------|
| `on_delete=models.CASCADE` | 37 | **95** (파일 30개, 비-test/migrations) |
| `on_delete=models.SET_NULL` | 7 | **17** (파일 11개) |
| `on_delete=models.PROTECT` | – | 7 |
| `unique_together` | – | 28 (모델 코드만) |
| `UniqueConstraint` | – | 4 (portfolio만) |
| `update_or_create` 호출 | – | 124 (test 제외) |
| `'stocks.Stock'` FK 참조 | – | 32 |

---

## 1. FK orphan 위험

### 1-1. SET_NULL 사용처 전수 (17건)

| 파일:라인 | 대상 | null 허용 후 정리 로직 |
|-----------|------|---------------------|
| `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` → Stock | ✅ `rematch_unmatched.py` management command + `signals.py` post_save (`on_unmatched_resolved`) — 유일하게 정리 경로 있음 |
| `serverless/models.py:660` | `ScreenerAlert.preset` → ScreenerPreset | ❌ orphan alert 잔존 |
| `serverless/models.py:808` | `InvestmentThesis.user` → User | ❌ 사용자 탈퇴 시 thesis 영구 잔존 (의도 가능) |
| `serverless/models.py:1409` | `AdminActionLog.user` → User | 🟢 감사 로그 의도된 보존 |
| `rag_analysis/models.py:145` | `AnalysisSession.basket` → DataBasket | ❌ basket 삭제 후 세션 무의미 잔존 |
| `rag_analysis/models.py:256` | `UsageLog.session` → AnalysisSession | 🟢 비용 추적 의도된 보존 |
| `rag_analysis/models.py:263` | `UsageLog.message` → AnalysisMessage | 🟢 비용 추적 의도된 보존 |
| `chainsight/models/news_event.py:54` | `NewsEvent.parent_event` → self | ❌ 자기참조 NULL — 트리 끊김 |
| `macro/models/indicators.py:310` | (관련 모델) | ❌ |
| `portfolio/models.py:327` | (analysis_run 등) | ❌ |
| `portfolio/models.py:732` | `ChatSession.analysis_run` → AnalysisRun | 🟢 의도된 느슨한 연결(코멘트 명시) |
| `portfolio/models.py:831` | (coach 관련) | ❌ |
| `thesis/models/monitoring.py:66` | (thesis 모델) | ❌ |
| `thesis/models/indicator.py:15` | (thesis 모델) | ❌ |
| `thesis/models/thesis.py:70` | (thesis 모델) | ❌ |
| `thesis/models/thesis.py:77` | (thesis 모델) | ❌ |
| `marketpulse/models/anomaly.py:25` | (anomaly 모델) | ❌ |

**위험 평가**: 17건 중 14건이 SET_NULL 이후 orphan 정리 로직 부재. 단 1건(sec_pipeline)만 `signals.py`에서 재매칭 트리거 + management command 보유.

### 1-2. orphan 누적 탐지 부재

```bash
# 현재 코드베이스에서 isnull=True 필터 사용처 (운영용)
sec_pipeline/signals.py:44             target_company__isnull=True
sec_pipeline/management/commands/rematch_unmatched.py:33,51
sec_pipeline/intelligence.py:92        match_unmatched = recent_ev.filter(target_company__isnull=True)
sec_pipeline/quality_checks.py:143     'unmatched': ...
```

→ sec_pipeline 외에는 SET_NULL FK가 NULL이 된 후 **얼마나 누적되었는지 카운트하는 정기 작업 없음**.

### 1-3. 권장 액션

- `serverless.InvestmentThesis.user IS NULL`, `rag_analysis.AnalysisSession.basket IS NULL` 등을 주간 quality_checks에 추가
- `chainsight.NewsEvent.parent_event IS NULL` 자식 노드를 고아 이벤트로 처리하는 정책 명문화

---

## 2. CASCADE 체인 분석

### 2-1. 파일별 CASCADE 사용 개수 (실측)

```
12 portfolio/models.py
 8 graph_analysis/models.py
 6 users/models.py
 6 stocks/models.py
 6 sec_pipeline/models.py
 5 thesis/models/learning.py
 5 rag_analysis/models.py
 4 thesis/models/community.py
 4 serverless/models.py
 4 metrics/models/benchmark.py
 3 validation/models/peer_preset.py
 3 macro/models/relationships.py
 2 thesis/models/{indicator,monitoring,thesis}.py
 2 marketpulse/models/news.py
 2 macro/models/indicators.py
 2 news/models.py
 2 chainsight/models/saved_path.py
 1 chainsight/models/{sensitivity,revenue_structure,narrative_tag,insider_signal,growth_stage,event_reaction,chain_profile,capital_dna}.py
 1 validation/models/{news_summary,category_score,benchmark_delta,metric_latest}.py
 1 metrics/models/metric_snapshot.py
```

### 2-2. Stock 삭제 시 영향 범위 (가장 큰 cascade fan-out)

`Stock`을 가리키는 FK 32개 중 **CASCADE 27개 / SET_NULL 1개 / PROTECT 4개**.

**Stock 1개 삭제 시 즉시 멸실되는 도메인** (CASCADE 트리):

| 앱 | 사라지는 모델 (예시) |
|----|---------------------|
| stocks | DailyPrice, WeeklyPrice, IncomeStatement (×4 finance), StockOverviewKo, StockNews |
| users | Portfolio.stock 참조 row, WatchlistItem |
| chainsight | ChainProfile, NarrativeTag, Sensitivity, GrowthStage, EventReaction, CapitalDNA, RevenueStructure, InsiderSignal (각 모델 row) |
| validation | CompanyMetricLatest, CompanyBenchmarkDelta, CategorySignal, NewsSummary, PeerPreset.target |
| metrics | CompanyMetricSnapshot (`on_delete=CASCADE`) |
| sec_pipeline | RawDocumentStore (Stock 기준) → CASCADE → SupplyChainEvidence(source) & BusinessModelSnapshot → CASCADE → BusinessModelEvidence  *(3단 체인)* |
| serverless | StockKeyword (관련), 일부 |
| macro | 관계 모델 |
| marketpulse | News 매칭 |

**연쇄 깊이**: `Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence` = **4단계 CASCADE**

→ Stock 1건 삭제는 사실상 *해당 종목과 관련된 모든 시계열·관계·문서·메트릭·뉴스·테제 데이터를 즉시 비가역적으로 삭제*하며, 단일 트랜잭션 안에서 락 경합 + lock timeout 위험.

### 2-3. PROTECT 사용처 (의도된 차단)

| 파일:라인 | 대상 | 의도 |
|-----------|------|------|
| `chainsight/models/news_event.py:23` | NewsEvent.stock → Stock | 뉴스 이벤트는 종목 삭제로부터 보호 |
| `metrics/models/metric_snapshot.py:11` | snapshot.metric_def → MetricDefinition | 정의 보호 |
| `portfolio/models.py:90, 393, 495, 566` | AnalysisRun/Card 등 → Stock | 분석 결과 보호 |
| `marketpulse/models/snapshot.py:51` | Snapshot.stock → Stock | 스냅샷 보호 |

→ 위 7건의 PROTECT가 있어 Stock CASCADE delete는 ProtectedError로 **현재는 그냥 실패**한다. 즉 운영에서 Stock 직접 삭제는 사실상 차단되어 있지만, 사용자/관리자가 PROTECT를 한 번 해제하면 즉시 CASCADE 쓰나미 발생 가능.

### 2-4. 다단계 CASCADE 체인 (3단 이상)

| 깊이 | 체인 |
|------|------|
| 4단 | `Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence` |
| 3단 | `Stock → RawDocumentStore → SupplyChainEvidence` + (FK 가지 `Stock` SET_NULL) |
| 3단 | `User → DataBasket → AnalysisSession → AnalysisMessage` (rag_analysis: 각 단계 CASCADE) |
| 3단 | `User → Portfolio → PortfolioHolding` (`portfolio/models.py`) |
| 3단 | `AnalysisRun → MetricResult` & `AnalysisRun → DiagnosticCard` (둘 다 CASCADE) |
| 3단 | `User → Watchlist → WatchlistItem` (`users/models.py`) |

### 2-5. graph_analysis 자기참조 cascade (8건)

`graph_analysis/models.py`에 CASCADE 8개 — Node, Edge가 서로 cascade로 묶이면 그래프 1개 삭제가 거대한 sub-tree drop을 유발할 수 있다. 현재 API 미구현 상태(CLAUDE.md 명시)지만 모델은 활성 마이그레이션 상태이므로 추후 enable 시 검증 필요.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3-1. neo4j_dirty 플래그 통일 현황 (audit P0 #9 결과)

**완료된 통일**:
- `chainsight/models/chain_profile.py:65` — `neo4j_dirty = BooleanField(default=True, db_index=True)` + `neo4j_synced_at`
- `chainsight/models/relation_discovery.py:130` — 동일 패턴 + index
- `sec_pipeline/models.py:100` — 동일 패턴 + `Index(fields=['neo4j_dirty'])`
- `chainsight/migrations/0008_unify_neo4j_flags.py` — `neo4j_synced` 반전, `synced_to_neo4j` 제거 완료
- 모든 큐와 task가 `dirty=True` 단일 의미로 통일

**바람직한 패턴**:
- `RelationConfidence.save()`에서 `self.neo4j_dirty = True` 자동 토글 (relation_discovery.py:158)
- `queryset.update(...)` 같이 save() 우회 경로에선 명시적으로 `neo4j_dirty=True` 함께 (relation_tasks.py:388, 395, 402)

### 3-2. 동기화 실패 시 재시도 메커니즘

| 위치 | 정책 |
|------|------|
| `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` | `max_retries=2, default_retry_delay=60` |
| `chainsight/tasks/sync_tasks.py:14,97,148` | `max_retries=1` (profile/relation 메인 태스크) |
| `sec_pipeline/tasks.py:337` (`sync_dirty_to_neo4j`) | `max_retries=1, soft_time_limit=300` + Phase A에서 `select_for_update(skip_locked=True)` |
| `sec_pipeline/tasks.py:22,148` (수집) | `max_retries=3,5` + exponential backoff (`60 * 2**retries`, `10 * 2**retries`) |

**위험 포인트**:
- `chainsight/services/neo4j_sync.py:42-43` — Neo4j upsert 예외 발생 시 `except Exception as e: logger.error(...)` 후 continue. 실패한 row의 `neo4j_dirty`는 그대로 True 유지되므로 다음 사이클에서 재시도되는 구조 자체는 OK이나, **알림 없음** → 영구 실패 row 누적 가능.
- `chainsight` task `max_retries=1`은 매우 낮음. 일시 Neo4j 장애에 취약. sec_pipeline 동일.

### 3-3. PG ↔ Neo4j 불일치 감지

| 항목 | sec_pipeline | chainsight |
|------|-------------|-----------|
| dirty 적체 카운트 알림 | ✅ `quality_checks.py:90-97` (50건 초과 시 alert) | ❌ |
| unmatched 카운트 알림 | ✅ (100건 초과) | ❌ |
| `neo4j_synced_at` 오래된 row 추적 | ❌ (필드는 있으나 staleness 검사 없음) | ❌ |
| Neo4j 쿼리 결과 vs PG count 일치 검사 | ❌ | ❌ |
| Admin 대시보드 노출 | ✅ `intelligence.py:97-98`, `quality_checks.py:144-147`, `admin.py:30-32` | 부분 (admin 코드는 있으나 dirty backlog 알림 없음) |

**결론**: sec_pipeline은 dirty 적체와 unmatched를 모니터링하지만, *PG에는 있고 Neo4j에는 없는 (반대 포함) 불일치를 비교하는 reconcile job은 양쪽 모두 부재*. 현재는 "PG가 truth, Neo4j는 거기서 빌드"라는 단방향 가정에 의존.

---

## 4. UniqueConstraint / update_or_create 현황

### 4-1. unique 제약 사용 통계

- `unique_together`: **28건** (모델 정의에서, test/migration 제외)
- `UniqueConstraint`: **4건** (전부 `portfolio/models.py`)

**`UniqueConstraint`로 마이그레이션된 사례 (portfolio만)**:
- `portfolio/models.py:439` `unique_metric_result_per_run_stock` (analysis_run+stock+metric_id)
- `portfolio/models.py:525` `unique_card_priority_per_run` (analysis_run+priority)
- `portfolio/models.py:583` 추가 제약
- `portfolio/models.py:701` `unique_percentile_cache` (metric_id+industry_code+date)

**비일관 신호**:
- Django 5.x에서는 `UniqueConstraint`가 권장(named, condition 지원). 28건의 `unique_together`는 여전히 deprecated 형태로 남아있음 — 이름 없는 unique index 라 추후 mig 충돌 가능.

### 4-2. update_or_create race condition 가능성

총 **124 호출**, 대표적 호출 위치:

| 위치 | 트랜잭션 | unique key | race 위험 |
|------|---------|-----------|----------|
| `api_request/stock_service.py:254,390,417,481,532,581,678` | ✅ `with transaction.atomic()` 감싸짐 | symbol, date 등 unique_together | 🟢 LOW |
| `serverless/tasks.py:393` `StockKeyword.update_or_create` | ❌ 미감싸짐 | 없음 명시 | 🔴 동일 키 동시 호출 시 두 row 모두 생성 가능 |
| `serverless/tasks.py:1425` `StockRelationship.update_or_create` | ❌ | unique `[source_symbol, target_symbol, relationship_type]` | 🟡 IntegrityError 산발 |
| `serverless/services/theme_matching_service.py:247,329,575` | 일부만 atomic | unique `[stock_symbol, theme_id]` | 🟡 |
| `serverless/services/news_relation_matcher.py:201` | ❌ | unique | 🟡 |
| `chainsight/tasks/relation_tasks.py:275` `RelationConfidence.update_or_create` | ❌ | unique `[symbol_a, symbol_b, relation_type]` | 🟡 — Celery 다중 worker 동시 실행 시 IntegrityError |
| `chainsight/tasks/profile_tasks.py:106,180` | ❌ | unique `symbol`(OneToOne 추정) | 🟡 |
| `chainsight/tasks/insider_tasks.py:117,162` | ❌ | unique | 🟡 |

**Django ORM 사실관계**:
- `update_or_create`는 내부에서 `try: get; except DoesNotExist: create`를 수행. 두 worker가 동시에 get 실패 후 create하면 두 번째는 unique violation으로 IntegrityError.
- Django는 이를 알고 **단일 실패 후 재시도(get)**까지는 해주지만, 다중 worker 환경에서는 여전히 IntegrityError가 노출될 수 있다 (`select_for_update`로 락이 필요).

**현재 방어 수준**:
- transaction.atomic 사용처 20여개 — `update_or_create`를 감싸지 않은 코드가 100건 이상.
- `select_for_update` 사용처는 `rag_analysis/views.py`, `sec_pipeline/tasks.py` 등 소수.

### 4-3. unique_together 모델별 (운영 중요 항목)

| 모델 | unique_together | 위험 |
|------|-----------------|------|
| `stocks.DailyPrice/WeeklyPrice` | (stock, date) | 🟢 — atomic 감싼 호출만 사용 |
| `stocks.IncomeStatement/BalanceSheet/CashFlow` | (stock, period_type, fiscal_year, fiscal_quarter) | 🟢 |
| `serverless.MarketMover` | (date, mover_type, symbol) | 🟢 — data_sync.py에서 atomic |
| `serverless.StockRelationship` | (source_symbol, target_symbol, relationship_type) | 🟡 — 다수 호출 atomic 미적용 |
| `serverless.ETFHolding` | (etf, stock_symbol, snapshot_date) | 🟢 |
| `chainsight.NewsEvent` | (source, source_id) | 🟢 |
| `chainsight.PriceCoMovement` | (symbol_a, symbol_b, period) | 🟡 |
| `chainsight.RelationConfidence` | (symbol_a, symbol_b, relation_type) | 🔴 — relation_tasks Celery 다중 worker 동시 호출 가능 |
| `metrics.CompanyMetricSnapshot` | (symbol, fiscal_year, metric_code) | 🟢 |
| `metrics.IndustryMetricBenchmark` | (industry, fiscal_year, metric_code) | 🟢 |

---

## 부록: 핵심 권장 액션 (우선순위)

| 우선순위 | 액션 | 영향 |
|---------|------|------|
| P0 | chainsight에 dirty backlog quality check 추가 (sec_pipeline 패턴 복제) | 동기화 영구 실패 detection |
| P0 | Stock 삭제는 admin/관리 명령으로만, soft-delete 패턴 도입 검토 | 4단 CASCADE 쓰나미 차단 |
| P1 | Celery에서 호출하는 `update_or_create` 27건을 `transaction.atomic` + `select_for_update` 로 감싸기 | IntegrityError 산발 제거 |
| P1 | `serverless.InvestmentThesis.user` 등 SET_NULL orphan 7건 주간 카운트 알림 추가 | orphan 누적 감시 |
| P2 | PG↔Neo4j reconcile job (count diff + sample row 비교) 추가 | 양방향 동기화 검증 |
| P2 | `unique_together` 28건을 `UniqueConstraint(name=...)` 로 점진 마이그레이션 | Django 6 호환성 + 이름 기반 lookup |
| P3 | `graph_analysis` 활성화 전 자기참조 CASCADE 8건 재검토 | 그래프 sub-tree drop 위험 사전 차단 |

---

*보고서 종료 — 본 문서는 코드 변경 없이 정적 분석만 수행했습니다.*
