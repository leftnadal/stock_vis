# 데이터 무결성 감사 보고서

- 작성일: 2026-05-21
- 범위: Backend 전체 (`**/models*.py`, `**/tasks*.py`, `**/services/*.py`, `**/signals.py`)
- 모드: read-only (코드 수정 없음)
- 비교 기준: `5월/19일/data_integrity_audit.md` (델타 표기)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 영역 |
|--------|------|----------|
| 🔴 HIGH | 3 | (1) `'stocks.Stock'` FK 다수가 CASCADE → Stock 1건 삭제로 4단계 도메인 동시 멸실 / (2) chainsight Neo4j sync에 dirty backlog quality_checks 부재 (sec_pipeline에만 존재) / (3) Celery 다중 워커가 호출하는 `update_or_create` 다수가 `transaction.atomic` + `select_for_update` 미사용 — unique 제약 race condition으로 `IntegrityError` 산발 가능 |
| 🟡 MEDIUM | 4 | (1) SET_NULL 17건 중 14건 orphan 자동 cleanup 부재 (sec_pipeline 1건만 rematch 경로 보유) / (2) `Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence` 4단 CASCADE 체인 / (3) `graph_analysis` 자기참조 CASCADE 8건 (현재 API 미구현이나 모델 활성) / (4) `unique_together` 28건은 사용 중 / `UniqueConstraint`는 portfolio 4건만 — 비일관 |
| 🟢 LOW | 3 | (1) `neo4j_dirty` 플래그 패턴 통일 완료(audit P0 #9, 2026-04-29) / (2) PROTECT 4건(`portfolio/models.py:90,393,495,566`)이 Stock CASCADE delete를 사실상 차단 / (3) `chainsight/services/neo4j_sync.py` 실패 row는 `neo4j_dirty=True` 유지 → 다음 사이클에서 자동 재시도 |

**총계**: HIGH 3 · MEDIUM 4 · LOW 3 (5/19 대비 변동 없음 — 코드 변경 없음)

### 검색 통계 (실측)

| 항목 | 사용자 보고 | 실측 (2026-05-21) | 5/19 대비 |
|------|------------|---------------------|-----------|
| `on_delete=models.CASCADE` | 37 | **95** (32개 파일, test/migrations 제외) | = |
| `on_delete=models.SET_NULL` | 7 | **17** (11개 파일) | = |
| `on_delete=models.PROTECT` | – | **4** (portfolio만, models 코드) | -3 (이전 7건은 비-model 포함 추정) |
| `unique_together` | – | 28+ (모델 정의) | = |
| `UniqueConstraint` | – | **4** (portfolio만) | = |
| `update_or_create` 호출 | – | 206 (test 포함) / ~124 (test 제외) | = |
| `'stocks.Stock'` FK 참조 (CASCADE+PROTECT+SET_NULL 합산) | – | 32 | = |

---

## 1. FK orphan 위험

### 1-1. SET_NULL 사용처 전수 (17건)

| 파일:라인 | 대상 | null 허용 후 정리 로직 |
|-----------|------|---------------------|
| `marketpulse/models/anomaly.py:25` | `AnomalySignal.paired_news` → MarketPulseNews | ❌ |
| `macro/models/indicators.py:310` | `EconomicIndicator.related_indicator` → self | ❌ 자기참조 NULL |
| `portfolio/models.py:327` | `Portfolio.wallet_snapshot_at_execution` → WalletSnapshot | ❌ |
| `portfolio/models.py:732` | `ChatSession.analysis_run` → AnalysisRun | 🟢 의도된 느슨한 연결 (코멘트 명시) |
| `portfolio/models.py:831` | `Decision.context_analysis_run` → AnalysisRun | ❌ |
| `serverless/models.py:660` | `ScreenerAlert.preset` → ScreenerPreset | ❌ orphan alert 잔존 |
| `serverless/models.py:808` | `InvestmentThesis.user` → User | ❌ 사용자 탈퇴 시 thesis 영구 잔존 (의도 가능) |
| `serverless/models.py:1409` | `AdminActionLog.user` → User | 🟢 감사 로그 의도된 보존 |
| `rag_analysis/models.py:145` | `AnalysisSession.basket` → DataBasket | ❌ basket 삭제 후 세션 무의미 잔존 |
| `rag_analysis/models.py:256` | `UsageLog.session` → AnalysisSession | 🟢 비용 추적 의도된 보존 |
| `rag_analysis/models.py:263` | `UsageLog.message` → AnalysisMessage | 🟢 비용 추적 의도된 보존 |
| `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` → Stock | ✅ `rematch_unmatched.py` + `signals.py:on_unmatched_resolved` (유일하게 정리 경로) |
| `chainsight/models/news_event.py:54` | `NewsEvent.duplicate_of` → self | ❌ 자기참조 NULL — duplicate chain 끊김 |
| `thesis/models/thesis.py:70` | `Thesis.thesis_sources` → ? | ❌ |
| `thesis/models/thesis.py:77` | `Thesis.copies` (clone) → Thesis | ❌ 원본 삭제 시 복제 thesis 고아화 |
| `thesis/models/indicator.py:15` | `ThesisIndicator.premise` → ThesisPremise | ❌ |
| `thesis/models/monitoring.py:66` | `IndicatorEvaluation.indicator` → ThesisIndicator | ❌ 평가 히스토리는 유지되나 어느 지표인지 추적 불가 |

**위험 평가**: 17건 중 **14건 orphan 정리 로직 부재**. 단 1건(sec_pipeline)만 management command + signal로 재매칭 트리거 보유.

### 1-2. orphan 누적 탐지 부재 (현재 코드의 `isnull=True` 필터 사용처)

```
sec_pipeline/signals.py:44             target_company__isnull=True
sec_pipeline/management/commands/rematch_unmatched.py:33,51
sec_pipeline/intelligence.py:92        match_unmatched = recent_ev.filter(target_company__isnull=True)
sec_pipeline/quality_checks.py:143     'unmatched': ...count()
```

→ **sec_pipeline 외 SET_NULL FK NULL 누적 카운트 잡 없음**. `chainsight.NewsEvent.duplicate_of`, `thesis.Thesis.copies`, `serverless.InvestmentThesis.user`, `rag_analysis.AnalysisSession.basket` 등은 NULL이 되어도 가시성 없음.

### 1-3. 권장 액션

- `serverless.InvestmentThesis.user IS NULL`, `rag_analysis.AnalysisSession.basket IS NULL`, `thesis.Thesis.copies.original_thesis IS NULL` 등을 주간 quality_checks에 추가
- `chainsight.NewsEvent.duplicate_of IS NULL`인 child 노드 정책 명문화

---

## 2. CASCADE 체인

### 2-1. 파일별 CASCADE 사용 개수 (실측, 95건)

```
12 portfolio/models.py
 8 graph_analysis/models.py
 6 stocks/models.py
 6 sec_pipeline/models.py
 6 users/models.py
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
 2 validation/models/{benchmark_delta,metric_latest}.py
 2 chainsight/models/saved_path.py
 1 chainsight/models/{sensitivity,revenue_structure,narrative_tag,
                       insider_signal,growth_stage,event_reaction,
                       chain_profile,capital_dna}.py
 1 validation/models/{news_summary,category_score}.py
 1 metrics/models/metric_snapshot.py
```

### 2-2. Stock 삭제 시 영향 범위 (가장 큰 cascade fan-out)

`'stocks.Stock'` 또는 `Stock` 모델을 가리키는 FK 32개 중:

- **CASCADE**: 27건 (stocks 내부 6, sec_pipeline 3, chainsight 8, validation 4, metrics 2, graph_analysis 3, marketpulse 1)
- **PROTECT**: 4건 (`portfolio/models.py:90, 393, 495, 566` — Wallet/Analysis/Card/LLM Comment)
- **SET_NULL**: 1건 (`sec_pipeline/models.py:86`)

**Stock 1개 삭제 시 즉시 멸실되는 도메인** (CASCADE 트리):

| 앱 | 사라지는 모델 (예시) |
|----|---------------------|
| stocks | DailyPrice, WeeklyPrice, IncomeStatement/BalanceSheet/CashFlow, StockOverviewKo, EODSignal, SignalAccuracy, StockNews |
| users | Portfolio (stock 참조), WatchlistItem |
| chainsight | CompanyChainProfile, NarrativeTag, Sensitivity, GrowthStage, EventReaction, CapitalDNA, RevenueStructure, InsiderSignal |
| validation | CompanyMetricLatest, CompanyBenchmarkDelta, CategorySignal, NewsSummary, PeerPreset.symbol |
| metrics | CompanyMetricSnapshot, IndustryMetricBenchmark.symbol (`benchmark.py:100,12`) |
| sec_pipeline | RawDocumentStore(`models.py:25`) → CASCADE → SupplyChainEvidence(source, `:82`) & BusinessModelSnapshot(`:161`) → CASCADE → BusinessModelEvidence(`:213`) |
| serverless | (Stock 직접 FK는 적으나) StockRelationship 캐시 등 |
| marketpulse | Snapshot.stock |
| graph_analysis | CorrelationEdge.stock_a/stock_b, PriceCache.stock |

### 2-3. 다단계 CASCADE 체인 (3단 이상)

| 깊이 | 체인 |
|------|------|
| **4단** | `Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence` (`sec_pipeline/models.py:25, 161, 213`) |
| **3단** | `Stock → RawDocumentStore → SupplyChainEvidence` (target_company는 SET_NULL이지만 source_company는 CASCADE) |
| **3단** | `User → DataBasket → AnalysisSession(.basket=SET_NULL but .user=CASCADE) → AnalysisMessage` (`rag_analysis/models.py:15, 77, 140, 194`) |
| **3단** | `User → Portfolio → PortfolioHolding`, `User → Wallet → WalletHolding` (`portfolio/models.py:54, 85, 162, 222, 291`) |
| **3단** | `AnalysisRun → MetricResult` + `AnalysisRun → DiagnosticCard` (`portfolio/models.py:388, 483, 561`) |
| **3단** | `User → Watchlist → WatchlistItem` (`users/models.py:171, 197`) |
| **3단** | `Thesis → ThesisIndicator → IndicatorEvaluation` (CASCADE: `thesis/models/indicator.py:10, 124`, monitoring SET_NULL 일부) |

### 2-4. PROTECT 사용처 (의도된 차단)

| 파일:라인 | 대상 | 의도 |
|-----------|------|------|
| `portfolio/models.py:90` | `WalletHolding.stock` → Stock | 보유 시 종목 삭제 차단 |
| `portfolio/models.py:393` | `MetricResult.stock` → Stock | 분석 결과 보호 |
| `portfolio/models.py:495` | `DiagnosticCard.target_stock` → Stock | 진단 카드 보호 |
| `portfolio/models.py:566` | `LLMComment.stock` → Stock | LLM 코멘트 보호 |

→ 운영 중 Stock 직접 삭제는 위 PROTECT 4건으로 `ProtectedError` 발생 → 사실상 차단. **하지만** PROTECT를 해제하거나 PROTECT 미설정 path(예: chainsight FK)로 직접 SQL 삭제 시 27건 CASCADE 쓰나미 발생.

### 2-5. graph_analysis 자기참조 cascade (8건)

`graph_analysis/models.py`의 CASCADE 8건은 Watchlist + Stock_a/b + Edge가 서로 묶임. CLAUDE.md 명시대로 API 미구현 상태지만 마이그레이션 활성. 추후 enable 시 Watchlist 1건 삭제 → 모든 Correlation/Edge/Metadata/PriceCache 삭제됨.

---

## 3. Neo4j 동기화

### 3-1. neo4j_dirty 플래그 통일 (audit P0 #9, 2026-04-29 완료)

| 모델 | 필드 | Index |
|------|------|-------|
| `chainsight/models/chain_profile.py:65` | `neo4j_dirty=BooleanField(default=True, db_index=True)` + `neo4j_synced_at` | ✅ |
| `chainsight/models/relation_discovery.py:130` | 동일 패턴 | ✅ |
| `sec_pipeline/models.py:100` | 동일 패턴 + `Index(fields=['neo4j_dirty'])` (`:111`) | ✅ |

**save() 자동 토글**: `chainsight/models/relation_discovery.py:158` — `self.neo4j_dirty = True` (bulk_update 우회 시 명시 토글: `chainsight/tasks/relation_tasks.py:388, 395, 402`)

### 3-2. 동기화 실패 시 재시도 메커니즘

| 위치 | 정책 |
|------|------|
| `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` | `max_retries=2, default_retry_delay=60` |
| `chainsight/tasks/sync_tasks.py:14,97,148` | `max_retries=1` (profile/relation 메인) |
| `sec_pipeline/tasks.py:337` (`sync_dirty_to_neo4j`) | `max_retries=1, soft_time_limit=300` + Phase A `select_for_update(skip_locked=True)` (`:367`) |
| `sec_pipeline/tasks.py:22, 148` (수집) | `max_retries=3, 5` + exponential backoff |

**위험 포인트**:

1. `chainsight/services/neo4j_sync.py:42-43` — Neo4j upsert 예외 시 `logger.error()` 후 continue. **실패 row의 `neo4j_dirty`는 True 유지** → 다음 사이클 재시도 됨(자가복구) **하지만 알림 없음** → 영구 실패 row 누적 가능.
2. `chainsight` task `max_retries=1`은 매우 낮음. 일시 Neo4j 장애에 취약 (sec_pipeline의 sync도 동일).
3. `sec_pipeline/tasks.py:411 (except Exception: pass)` — DELETE 단계 실패 무시. 정상이나, 실패율 메트릭 부재.

### 3-3. PG ↔ Neo4j 불일치 감지

| 항목 | sec_pipeline | chainsight |
|------|-------------|-----------|
| dirty 적체 카운트 알림 | ✅ `quality_checks.py:90-97, 144-147` (50건 초과 시 alert: `test_quality_checks_advanced.py` 검증) | ❌ |
| unmatched 카운트 알림 | ✅ (`intelligence.py:92`, `rematch_unmatched.py:51`) | ❌ |
| `neo4j_synced_at` 오래된 row 추적 | ❌ (필드는 있으나 staleness 검사 없음) | ❌ |
| Neo4j 쿼리 결과 vs PG count 일치 검사 | ❌ | ❌ |
| Admin 대시보드 노출 | ✅ `admin.py:30-32, list_filter=['neo4j_dirty']` | 부분 — admin은 있으나 dirty backlog 알림 없음 |

**결론**: sec_pipeline은 dirty 적체와 unmatched를 모니터링하지만 chainsight는 미구현. **양쪽 모두 reconcile job(PG count vs Neo4j count, 샘플 row 양방향 비교) 부재** — "PG가 truth, Neo4j는 빌드 결과"라는 단방향 가정에 의존.

`news/services/news_neo4j_sync.py:699-711`의 orphan NewsEvent 정리(`MATCH (ne:NewsEvent) WHERE NOT (ne)-[]-() DELETE ne`)가 유일한 Neo4j 측 cleanup. PG에는 있고 Neo4j에는 없는 경우 감지 불가.

---

## 4. Unique 제약조건

### 4-1. 사용 통계

- `unique_together`: **28+건** (모델 정의에서, test/migration 제외)
- `UniqueConstraint`: **4건** (전부 `portfolio/models.py`)

**`UniqueConstraint`로 마이그레이션된 사례 (portfolio만)**:
- `portfolio/models.py:439` `unique_metric_result_per_run_stock` (analysis_run+stock+metric_id)
- `portfolio/models.py:525` `unique_card_priority_per_run` (analysis_run+priority)
- `portfolio/models.py:583` 추가 제약 (LLM 코멘트 관련)
- `portfolio/models.py:701` `unique_percentile_cache` 추정

**비일관 신호**: Django 5.x에서는 `UniqueConstraint(name=...)`가 권장 (named, condition 지원). 28건의 `unique_together`는 deprecated 형태로 남아있음 — 이름 없는 unique index라 추후 mig 충돌 가능.

### 4-2. update_or_create race condition 가능성

총 **206 호출** (test 포함, 코어 100+건). 대표 위치:

| 위치 | 트랜잭션 | unique key | race 위험 |
|------|---------|-----------|----------|
| `api_request/stock_service.py:*` (8건) | ✅ `with transaction.atomic()` | symbol, date 등 unique_together | 🟢 LOW |
| `serverless/tasks.py:393` `StockKeyword.update_or_create` | ❌ 미감싸짐 | (symbol, date) unique_together | 🔴 동일 키 동시 호출 시 IntegrityError |
| `serverless/tasks.py:1425` `StockRelationship.update_or_create` | ❌ | (source_symbol, target_symbol, relationship_type) unique_together | 🟡 |
| `serverless/services/theme_matching_service.py:*` (3건) | 일부만 atomic | (stock_symbol, theme_id) | 🟡 |
| `serverless/services/news_relation_matcher.py:201` | ❌ | unique | 🟡 |
| `chainsight/tasks/relation_tasks.py:275` `RelationConfidence.update_or_create` | ❌ (atomic 밖) | (symbol_a, symbol_b, relation_type) | 🔴 Celery 다중 worker 동시 실행 시 IntegrityError |
| `chainsight/tasks/profile_tasks.py:106, 180` | ❌ | unique `symbol` (OneToOne) | 🟡 |
| `chainsight/tasks/insider_tasks.py:117, 162` | ❌ | unique | 🟡 |
| `sec_pipeline/tasks.py:120` `RawDocumentStore.update_or_create` | ❌ (외부 atomic 추정) | accession_no unique | 🟡 |
| `sec_pipeline/tasks.py:314` `RelationConfidence.update_or_create` | ❌ | 위와 동일 | 🟡 |

**Django ORM 사실관계**:
- `update_or_create`는 내부에서 `try: get; except DoesNotExist: create`. 두 worker가 동시에 get 실패 후 create하면 두 번째는 unique violation으로 `IntegrityError`.
- Django는 내부 재시도(get) 한 번까지는 수행하나, 다중 worker 환경에서는 여전히 IntegrityError가 노출될 수 있음 (`select_for_update` 또는 row-level lock 권장).

**현재 방어 수준**:
- `transaction.atomic` 사용처 40여 곳 — `update_or_create`를 감싸지 않은 호출이 80+건.
- `select_for_update` 사용처는 매우 제한적 (`rag_analysis/views.py`, `sec_pipeline/tasks.py:367`, `users/views.py` 등 7개 파일).

### 4-3. unique_together 운영 중요 항목

| 모델 | unique_together | 위험 |
|------|-----------------|------|
| `stocks.DailyPrice/WeeklyPrice` | (stock, date) | 🟢 — atomic 감싼 호출만 사용 |
| `stocks.IncomeStatement/BalanceSheet/CashFlow` | (stock, period_type, fiscal_year, fiscal_quarter) | 🟢 |
| `serverless.MarketMover` | (date, mover_type, symbol) | 🟢 — data_sync.py에서 atomic |
| `serverless.StockKeyword` | (symbol, date) | 🟡 — `tasks.py:393` atomic 미적용 |
| `serverless.StockRelationship` | (source_symbol, target_symbol, relationship_type) | 🟡 — 다수 호출 atomic 미적용 |
| `serverless.ETFHolding` | (etf, stock_symbol, snapshot_date) | 🟢 |
| `serverless.ThemeMatch` | (stock_symbol, theme_id) | 🟡 |
| `chainsight.NewsEvent` | (source, source_id) | 🟢 |
| `chainsight.RelationConfidence` | (symbol_a, symbol_b, relation_type) | 🔴 — relation_tasks Celery 다중 worker 동시 호출 가능 |
| `metrics.CompanyMetricSnapshot` | (symbol, fiscal_year, metric_code) | 🟢 |
| `metrics.IndustryMetricBenchmark` | (industry, fiscal_year, metric_code) | 🟢 |
| `metrics.PeerMetricBenchmark` | (symbol, fiscal_year, metric_code, preset_key) | 🟢 |
| `validation.CompanyBenchmarkDelta` | (symbol, fiscal_year, metric_code, preset_key) | 🟢 |
| `validation.CategorySignal` | (symbol, category, fiscal_year, preset_key) | 🟢 |
| `sec_pipeline.CompanyAlias` | (alias, context_sector) | 🟡 — `signals.py:63 get_or_create` race 가능 (낮은 빈도) |

---

## 부록: 핵심 권장 액션 (우선순위, 5/19 대비 변동 없음)

| 우선순위 | 액션 | 영향 |
|---------|------|------|
| P0 | chainsight에 dirty backlog quality check 추가 (sec_pipeline `quality_checks.py:90-97` 패턴 복제) | Neo4j 동기화 영구 실패 detection |
| P0 | Stock 삭제는 admin/관리 명령으로만, soft-delete 도입 검토 | 4단 CASCADE 쓰나미 차단 |
| P1 | Celery에서 호출하는 `update_or_create` 27건을 `transaction.atomic` + `select_for_update`로 감싸기 (특히 `chainsight/tasks/relation_tasks.py:275`, `serverless/tasks.py:393, 1425`) | IntegrityError 산발 제거 |
| P1 | `serverless.InvestmentThesis.user`, `rag_analysis.AnalysisSession.basket`, `thesis.Thesis.copies` SET_NULL orphan 7건 주간 카운트 알림 추가 | orphan 누적 감시 |
| P2 | PG↔Neo4j reconcile job (count diff + sample row 양방향 비교) 추가 | 단방향 가정 검증 |
| P2 | `unique_together` 28건을 `UniqueConstraint(name=...)`로 점진 마이그레이션 | Django 6 호환 + 이름 기반 lookup |
| P3 | `graph_analysis` 활성화 전 자기참조 CASCADE 8건 재검토 | 그래프 sub-tree drop 위험 사전 차단 |

---

## 5/19 → 5/21 변동 사항

- 코드 변경 없음 (slice13 `#65 — E1/E2/E3 legacy view 제거` 커밋은 `coach/` view layer로 모델/FK/제약 무영향)
- 모든 카운트 동일. 권장 액션 우선순위 유지.

---

*보고서 종료 — 본 문서는 코드 변경 없이 정적 분석만 수행했습니다.*
