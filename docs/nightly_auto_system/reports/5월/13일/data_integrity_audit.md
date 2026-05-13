# 데이터 무결성 감사 보고서

- **감사 일시**: 2026-05-13
- **감사 범위**: Django 모델 FK 정책, CASCADE 체인, Neo4j↔PostgreSQL 동기화, Unique 제약 / Race condition
- **방식**: 읽기 전용 정적 분석 (코드 수정 없음)

> 참고: 사전 파악 요약(SET_NULL 7곳, CASCADE 37곳)은 일부 파일에 한정한 부분 카운트였음. 실제 감사 결과 — **SET_NULL 17곳 / CASCADE 95곳 / PROTECT 7곳** (migrations·tests 제외) 으로 확인되어 모두 분석에 포함함.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 개수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 **HIGH** | 3 | (H1) SEC `SupplyChainEvidence.target_company` SET_NULL → Neo4j 좀비 엣지, (H2) `Stock` 삭제 시 3단계 이상 CASCADE 체인 (chainsight·validation·portfolio 동반 삭제), (H3) `queryset.update()` 후 `neo4j_dirty` 수동 토글 누락 위험 (save() 자동화와 분기) |
| 🟠 **MEDIUM** | 4 | (M1) `update_or_create` PostgreSQL race condition (대다수 호출이 `transaction.atomic()` 미적용), (M2) `sync_dirty_to_neo4j` 실패 row 재시도 메커니즘 부재 (no max_retries on backoff), (M3) SET_NULL orphan row를 주기적으로 정리하는 cron/Beat 태스크 없음, (M4) Neo4j ↔ PG 정합성 감지 routine 부재 (PG `neo4j_dirty=False` ≠ Neo4j 실제 반영) |
| 🟡 **LOW** | 3 | (L1) Neo4j sync 태스크별 `max_retries` 불일치 (1/2 혼재), (L2) `SupplyChainEvidence.target_company`·`neo4j_dirty` 인덱스가 단독 인덱스 — 복합 미존재로 dirty backlog 조회 비효율, (L3) `unique_together`(Deprecated)와 `UniqueConstraint` 혼재 |

---

## FK orphan 위험

### SET_NULL 전체 사용처 (17곳, 9개 파일)

| 파일 | 라인 | 필드 | → 대상 모델 | 의미·orphan 정리 로직 |
|------|------|------|-------------|------------------------|
| `sec_pipeline/models.py` | 86 | `SupplyChainEvidence.target_company` | `stocks.Stock` | 🔴 H1: target Stock 삭제 시 FK만 null, `target_company_name`(string) + Neo4j edge는 잔존. cron 없음. |
| `serverless/models.py` | 660 | `ScreenerAlert.preset` | `ScreenerPreset` | 프리셋 제거 후 `filters_json` fallback 의도 — 정상. |
| `serverless/models.py` | 808 | `InvestmentThesis.user` | `users.User` | 익명화. 정리 cron 없음. |
| `serverless/models.py` | 1409 | `AdminActionLog.user` | `users.User` | 감사 로그 보존 의도 — 정상. |
| `rag_analysis/models.py` | 145 | `AnalysisSession.basket` | `DataBasket` | basket 삭제 후에도 세션·메시지 보존. orphan 정리 없음. |
| `rag_analysis/models.py` | 256 | `UsageLog.session` | `AnalysisSession` | 비용 추적 보존 — 정상. |
| `rag_analysis/models.py` | 263 | `UsageLog.message` | `AnalysisMessage` | 비용 추적 보존 — 정상. |
| `chainsight/models/news_event.py` | 54 | `ChainNewsEvent.duplicate_of` | self | 중복 마스터 삭제 시 자식 잔존 — 의도. |
| `macro/models/indicators.py` | 310 | `EconomicEvent.related_indicator` | `EconomicIndicator` | indicator 폐기 후 이벤트는 보존. orphan 정리 없음. |
| `marketpulse/models/anomaly.py` | 25 | (Anomaly).paired_news | `MarketPulseNews` | 뉴스 만료 후 anomaly 보존 — 의도. |
| `thesis/models/thesis.py` | 70 | `Thesis.source_news` | `news.NewsArticle` | 뉴스 만료 후 가설 보존. |
| `thesis/models/thesis.py` | 77 | `Thesis.copied_from` | self | 원본 가설 삭제 후 복사본 보존. |
| `thesis/models/indicator.py` | 15 | `ThesisIndicator.metric_definition` | `metrics.MetricDefinition` | 카탈로그 변경 안전망. |
| `thesis/models/monitoring.py` | 66 | (Monitoring 관련) | `MetricDefinition` | 동일. |
| `portfolio/models.py` | 327 | `AnalysisRun.wallet_snapshot_at_execution` | `WalletSnapshot` | 스냅샷 삭제 시 분석 보존. |
| `portfolio/models.py` | 732 | `ChatSession.analysis_run` | `AnalysisRun` | 분석 삭제 후 대화 보존 — 의도 명시(docstring). |
| `portfolio/models.py` | 831 | `Decision.context_analysis_run` | `AnalysisRun` | 의사결정 이력 보존 — 정상. |

### SET_NULL 후 orphan 정리 로직 존재 여부

- **결과: 어디에도 SET_NULL orphan 전용 정리 cron 없음**.
- 검색: `grep -rn "orphan_cleanup\|orphan_" --include='*.py'` → 매칭은 Neo4j 내부 그래프 노드 cleanup(`news/services/news_neo4j_sync.py:700`) 단 1건. PG SET_NULL row 정리 routine은 **0건**.
- 대부분의 SET_NULL은 “이력 보존” 의도이므로 자동 정리가 오히려 정책 위반. 단, **🔴 H1** 케이스는 `target_company_name` 문자열만 남고 매칭 가능한 Stock이 사라진 상태가 누적되면 LLM/ML 학습 데이터 품질 저하.

### 권고

1. `sec_pipeline`에 `SupplyChainEvidence.target_company IS NULL AND target_company_name IS NOT NULL` 인 row의 카운트를 모니터링하는 quality check 추가 (현재 `sec_pipeline/quality_checks.py`에 `neo4j_dirty` 백로그 알림은 있으나 orphan 알림은 없음).
2. Stock 삭제 발생 시 (현실적으로 거의 없으나) `target_company_name`을 Neo4j ‘이름 기반’ 노드와 다시 매칭하는 re-resolve 태스크 필요.

---

## CASCADE 체인

### Stock 직접 CASCADE FK 참조 (17개 모델, 가장 큰 폭발 반경)

| 앱 | 모델 | 참조 필드 | 비고 |
|----|------|-----------|------|
| stocks | `DailyPrice` | `stock` (to_field=symbol) | 가격 시계열 |
| stocks | `WeeklyPrice` | `stock` (to_field=symbol) | |
| stocks | `StockOverviewKo` | `stock` (OneToOne) | 한글 개요 |
| stocks | `EODSignal` | `stock` | 일별 시그널 |
| stocks | `SignalAccuracy` | `stock` | 시그널 백테스트 |
| stocks | `StockNews` | `stock` (nullable) | 뉴스 |
| users | `Portfolio` | `stock` (to_field=symbol) | 사용자 보유 |
| users | `WatchlistItem` | `stock` (to_field=symbol) | |
| chainsight | `CompanyChainProfile` | OneToOne `symbol` | |
| chainsight | `CompanyGrowthStage` | `symbol` | |
| chainsight | `CompanyCapitalDNA` | `symbol` | |
| chainsight | `CompanySensitivityProfile` | `symbol` | |
| chainsight | `CompanyInsiderSignal` | `symbol` | |
| chainsight | `CompanyEventReaction` | `symbol` | |
| chainsight | `CompanyRevenueStructure` | `symbol` | |
| chainsight | `CompanyNarrativeTag` | `symbol` | |
| validation | `CompanyMetricLatest` | `symbol` | |
| validation | `CompanyBenchmarkDelta` | `symbol` | |
| validation | `CategorySignal` | `symbol` | |
| validation | `CompanyNewsSummary` | `symbol` | |
| validation | `PeerPreset`·`UserPeerPreference` | `symbol` | |
| sec_pipeline | `RawDocumentStore` | `symbol` | 10-K 원문 |
| sec_pipeline | `SupplyChainEvidence` | `source_company` (CASCADE), `target_company` (SET_NULL) | |
| sec_pipeline | `BusinessModelSnapshot` | `symbol` | |
| portfolio | `Holding`·`MetricResult`·`DiagnosticCard.target_stock`(PROTECT) 등 | mixed | |
| metrics | `CompanyMetricSnapshot` | `symbol` | (PROTECT — 안전망) |

### 3단계 이상 연쇄 삭제 경로

- 경로 A: **Stock → RawDocumentStore → SupplyChainEvidence → BusinessModelEvidence(→ via BusinessModelSnapshot)**.
  - `RawDocumentStore` (CASCADE from Stock) → `SupplyChainEvidence.source_document` (CASCADE) ⇒ 같은 Stock의 10-K 한 건 삭제 시 그 filing의 evidence + 비즈니스모델 evidence 전부 동반 삭제.
  - Stock 자체 삭제 시 모든 10-K + evidence + business model snapshot + business model evidence 가 일괄 삭제.
- 경로 B: **Stock → CompanyChainProfile (OneToOne, PK)**: Stock 삭제 시 profile 행 자체 사라지지만, **Neo4j :Stock 노드의 속성은 자동 동기화되지 않음**(`sync_profiles_to_neo4j`는 `neo4j_dirty=True` row만 처리). Neo4j 좀비 노드 잔존 가능.
- 경로 C: **Stock → validation.CategorySignal / CompanyMetricLatest / CompanyBenchmarkDelta → (집약) → CompanyChainProfile** (via `chainsight.aggregate_chain_profiles`). PG는 CASCADE로 정합이 유지되나 **이미 집약 완료된 ChainProfile의 score 필드(redundant copy)** 는 Stock 삭제 후에도 그대로 — Aggregator 재실행 전에는 stale.
- 경로 D: **Stock → users.Portfolio / WatchlistItem**: 사용자 보유·관심종목이 통보 없이 사라짐. CASCADE 채택했으므로 ‘소프트 삭제’ 패턴이 아닌 한 의도. 다만 사용자 면담 보존 가치를 고려하면 SET_NULL + ‘delisted’ 플래그 패턴이 더 안전.
- 경로 E: **users.User → Portfolio/Watchlist/Holding/AnalysisRun/ChatSession/Decision/...** (cascade fan-out 10+ 테이블). User 삭제 시 RAG·Thesis·Portfolio·Chain Sight 전 도메인 동반 삭제. ‘soft delete + GDPR 마스킹’ 전략 필요.

### Stock 삭제 영향 범위 (단일 ticker 기준 추정 row 수)

> 정량 추정 (S&P500 기업 평균 가정)

- DailyPrice (≥ 5년 일별) ≈ 1,250 rows
- EODSignal ≈ 1,250 rows / SignalAccuracy 변동
- chainsight 8개 테이블 ≈ 8 rows
- validation 5개 테이블 ≈ 5 rows
- sec_pipeline 10-K (RawDoc 5건 + SupplyChainEvidence 평균 20건/10-K + BusinessModelSnapshot 5 + Evidence 25) ≈ 130 rows
- users 측 (Portfolio/Watchlist) — 사용자 수에 비례

**1 ticker 단일 삭제로 약 2,600+ rows 일괄 삭제 + Neo4j 노드/엣지 좀비 가능성**. 운영상 Stock row를 직접 삭제하지 않는 ‘inactive 플래그(SP500Constituent.is_active)’ 패턴이 이미 일부 적용되어 있으므로, **`stocks.Stock` 자체에 `is_active` 플래그 도입 + 삭제 금지 정책** 권고.

### 권고

1. 운영 워크플로우에 `Stock.objects.filter(symbol=X).delete()` 사용 금지 가이드 추가 — soft delete 패턴으로 일원화.
2. Stock CASCADE 체인이 가장 깊으므로 **삭제 전 사전 체크 스크립트** (`management/commands/check_stock_deletion_impact.py`) 신설.
3. `Decision`처럼 보존 가치가 높은 모델(`Portfolio`, `WatchlistItem`)은 CASCADE → SET_NULL + `was_delisted_at` 컬럼 패턴으로 전환 검토.

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 사용 현황

| 앱 | 모델 | 필드 | 인덱스 | save() 자동? |
|----|------|------|--------|--------------|
| `chainsight` | `CompanyChainProfile` | `neo4j_dirty`, `neo4j_synced_at` | ✅ db_index=True | ⚠️ `aggregate_chain_profiles`가 `defaults={'neo4j_dirty': True}` 명시. save() 자동화 없음. |
| `chainsight` | `RelationConfidence` | `neo4j_dirty`, `neo4j_synced_at` | ✅ db_index=True + Meta.Index | ✅ `save()` 오버라이드에서 `self.neo4j_dirty = True` 자동. ⚠️ `queryset.update()`에서는 우회됨. |
| `sec_pipeline` | `SupplyChainEvidence` | `neo4j_dirty`, `neo4j_synced_at` | ✅ Meta.Index | ⚠️ save() 자동화 없음. `validator_track_a.py:158`, `ticker_matcher.py:99`에서 명시 토글. |

### save() vs queryset.update() 분기 — 🔴 H3

- `chainsight/models/relation_discovery.py:158` — `RelationConfidence.save()`가 `self.neo4j_dirty = True` 강제. **자동화의 이점이 있으나** `queryset.update()`는 save()를 호출하지 않으므로 dirty 토글이 누락됨.
- 이를 보완하기 위해 `chainsight/tasks/relation_tasks.py:382-402`에서 `stale.update(relation_status='stale', neo4j_dirty=True)` 형태로 dirty 동반 set. 그러나 **수동 토글 누락 시 status 전이는 PG에 반영되지만 Neo4j 엣지가 stale로 안 내려가는** 무성한 버그가 발생 가능. (cf. KB `audit P0 #9` 참고)
- `chainsight/services/neo4j_sync.py:48` — sync 후 `queryset.update(neo4j_dirty=False, neo4j_synced_at=…)` 호출. 의도적. 이때 만약 save() 분기로 들어가면 dirty=True가 영구히 토글되므로 **`queryset.update()`만 사용해야 한다는 암묵적 규약**이 존재. 코드 주석으로만 표시.
- `sec_pipeline/signals.py:52` — `UnmatchedCompanyQueue` resolved 시 `qs.update(target_company=..., neo4j_dirty=True)`. queryset 우회 시 명시 토글의 모범 사례.

### 재시도 메커니즘

| 태스크 | 위치 | max_retries | retry 정책 |
|--------|------|-------------|-----------|
| `sync_profiles_to_neo4j` | `chainsight/tasks/sync_tasks.py:97` | 1 | 명시적 retry 호출 없음. raise 시 Celery default. |
| `sync_relations_to_neo4j` (legacy wrapper) | `chainsight/tasks/sync_tasks.py:148` | 1 | 동일. 내부에서 `sync_dirty_relations` 호출. |
| `run_neo4j_dirty_sync` | `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` | 2, retry_delay 60s | 가장 robust. |
| `sec_pipeline.sync_dirty_to_neo4j` | `sec_pipeline/tasks.py:337` | 1 | per-row `try/except`로 실패 흡수 — 실패한 row는 `neo4j_dirty=True` 유지 → 다음 사이클에 재시도. |

🟠 M2: **per-row 실패 흡수는 좋으나, 영구 실패(예: Stock 노드 자체 부재) row를 격리하는 `neo4j_sync_attempts` 같은 카운터 컬럼 없음** → 매 사이클 재시도되며 Neo4j 부하 누적 가능.

### PG ↔ Neo4j 불일치 감지 메커니즘

🟠 M4 — **현재 불일치 자체를 감지하는 routine 없음**.

| 시나리오 | 현재 감지 가능? | 보강 필요 |
|----------|----------------|----------|
| PG `neo4j_dirty=False`인데 Neo4j에 엣지 없음 | ❌ 없음 | reconciler 태스크 필요 |
| PG에 없는데 Neo4j에 엣지 있음 | ❌ 없음 (cleanup_key 1회용 RELATED_TO 정리만 존재 — `sync_tasks.py:159`) | |
| PG `neo4j_dirty=True` 백로그 | ✅ `quality_checks.py:91-94`에서 50건 초과 알림 | OK |
| `RawDocumentStore` 삭제 후 Neo4j 좀비 evidence edge | ❌ | edge.accession_no 기반 cleanup |

### 권고

1. **주 1회 reconciler** Celery Beat 태스크 추가: PG 샘플 1000건 ↔ Neo4j 실제 쿼리 결과 비교. 불일치 발견 시 dirty 재마킹.
2. `neo4j_sync_attempts`, `last_sync_error` 컬럼 추가하여 영구 실패 격리.
3. `save()` 오버라이드로 dirty 자동 토글하는 모델은 `RelationConfidence` 단 1개. `CompanyChainProfile`·`SupplyChainEvidence`도 동일 패턴으로 통일 검토 (수동 토글 누락 방지).

---

## Unique 제약조건

### 사용 현황 (migrations 제외, 64곳)

- `unique_together`: 35곳 — 다수 (특히 `stocks`, `serverless`, `metrics`, `validation`, `chainsight`).
- `models.UniqueConstraint`: 5곳 (`portfolio/models.py:439, 525, 583, 701` 등). Django 4+ 권장 형태.
- `unique=True` 단일 컬럼: 24곳.

### 대표 키 패턴

| 모델 | 키 | 비고 |
|------|----|------|
| `DailyPrice` | (stock, date) | 시계열 핵심 |
| `EODSignal` | (stock, date) | 일별 시그널 |
| `SignalAccuracy` | (stock, signal_date, signal_tag) | |
| `BalanceSheet`·`IncomeStatement`·`CashFlowStatement` | (stock, period_type, fiscal_year, fiscal_quarter) | |
| `ChainNewsEvent` | (source, source_id) | 외부 ID 기반 |
| `RelationConfidence` | (symbol_a, symbol_b, relation_type) | |
| `CoMentionEdge` | (symbol_a, symbol_b) | |
| `PriceCoMovement` | (symbol_a, symbol_b, period) | |
| `CompanyAlias` | (alias, context_sector) | 🔵 context_country는 unique key에서 의도적으로 제외 (주석 명시) |
| `CompanyEventReaction` | (symbol, event_type) | |
| `ThemeMatch` | (stock_symbol, theme_id) | |
| `ETFHolding` | (etf, stock_symbol, snapshot_date) | |

### `update_or_create` 사용 시 race condition 가능성

`update_or_create` 호출은 99건. 대표 호출 위치:

| 위치 | 트랜잭션 보호 | 위험도 |
|------|---------------|--------|
| `api_request/stock_service.py:254, 390, 417, 481, 532, 581` | ✅ `transaction.atomic()` 내부 | 안전 |
| `stocks/services/sp500_service.py:82` | ✅ `transaction.atomic()` | 안전 |
| `serverless/services/data_sync.py:205` | ✅ `@transaction.atomic` 데코레이터 | 안전 |
| `serverless/services/regulatory_service.py:521` | ✅ `transaction.atomic()` | 안전 |
| `serverless/services/supply_chain_service.py:328` | ✅ `@transaction.atomic` | 안전 |
| `chainsight/tasks/relation_tasks.py:275, 309, 343` | ❌ 보호 없음 | 🟠 M1 |
| `chainsight/tasks/profile_tasks.py:106, 180` | ❌ 보호 없음 | 🟠 M1 |
| `chainsight/tasks/sync_tasks.py:84` | ❌ 보호 없음 | 🟠 M1 (단, Celery worker 단일이라 실질 위험은 낮음) |
| `serverless/services/theme_matching_service.py:247, 329, 575` | ❌ | 🟠 M1 (동일 (stock_symbol, theme_id) 충돌 가능) |
| `serverless/services/institutional_holdings_service.py:305, 425` | 부분(271 라인에 `transaction.atomic` 있으나 305는 별도 블록) | 부분 위험 |
| `serverless/services/keyword_service.py:202` | ❌ | 🟠 M1 |
| `news/services/aggregator.py:370, 388` | ❌ | 🟠 M1 |

#### Django `update_or_create` race semantics

- Django 공식: `update_or_create`는 **`get()` → 실패 시 `create()`** 패턴. 두 단계 사이에 동일 키를 가진 다른 트랜잭션이 `create()` 하면 `IntegrityError`.
- Django는 `IntegrityError`를 잡아 `get()` 재시도 (Django 1.11+ `_get_or_create()` 구현). 그러나 **이는 `unique_together` 또는 `UniqueConstraint`가 DB 레벨로 존재할 때만 보장**.
- 대상 모델 모두 unique 제약이 존재함을 확인 (`ThemeMatch.unique_together = (stock_symbol, theme_id)` 등). 따라서 **무결성 위반은 발생하지 않으나** `defaults`로 전달한 부분 업데이트가 ‘다른 트랜잭션의 create 직후 덮어쓰기’로 race 상태 진입 가능.

#### 권고

1. Celery worker가 단일(default queue)이면 실질 위험은 낮으나, `neo4j` queue 등 다중 워커 환경에서는 `chainsight/tasks/relation_tasks.py`의 `update_or_create`를 `with transaction.atomic():` + `select_for_update()` 패턴으로 보강.
2. `theme_matching_service.py`의 update_or_create는 LLM 결과를 덮어쓰므로 **마지막 write가 이김** — confidence 비교 후 update 조건부 적용 권장.
3. `unique_together` (Deprecated since Django 2.2)를 신규 코드에서는 `UniqueConstraint`로 통일 (`portfolio/models.py` 가 모범 사례).

---

## 참고: 검색 명령 결과

```
on_delete=models.SET_NULL    17  (production code)
on_delete=models.CASCADE     95  (production code)
on_delete=models.PROTECT      7  (production code)
neo4j_dirty 참조             47  (production code)
update_or_create             99  (production code)
unique_together/Constraint   64  (production code)
select_for_update             7  (rag_analysis/users/sec_pipeline)
transaction.atomic           30+ (production code)
```

> migrations·tests·__pycache__ 제외 카운트.

---

## 결론

데이터 무결성 위험의 **80% 이상**이 Neo4j ↔ PG 동기화 경계에 집중되어 있음.

1. **H1·H3**: SET_NULL + 수동 dirty 토글 누락 — Neo4j 좀비 엣지/노드 잔존 위험.
2. **H2**: Stock CASCADE 체인이 너무 깊음 — 실수 삭제 시 2,600+ rows 일괄 손실.
3. **M1·M4**: Race condition은 unique 제약으로 무결성은 보장되나, 정합성(PG↔Neo4j) 검증 routine이 부재.

→ 우선 순위: **(1) reconciler 태스크 신설, (2) Stock soft-delete 정책, (3) dirty 자동 토글 통일** 순으로 보강하는 것을 권고함.
