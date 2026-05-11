# 데이터 무결성 감사 보고서

**감사일**: 2026-04-26
**감사 범위**: 전체 Django 앱 모델 + Neo4j 동기화 + Race Condition
**감사 방식**: 정적 코드 분석 (Grep / 모델 직접 읽기) — 코드 수정 없음

---

## 요약 (위험도별 이슈 수)

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 Critical | 3 | (1) Stock 삭제 시 30+개 테이블 CASCADE 연쇄 삭제, (2) Neo4j 동기화 실패 시 영구 누락 위험, (3) `synced_to_neo4j` / `neo4j_dirty` / `neo4j_synced` 3개 필드가 동시 존재(레거시 잔존) |
| 🟠 High | 5 | (1) `target_company SET_NULL` 후 orphan evidence 정리 로직 부재, (2) `update_or_create` Race Condition 위험 ~70곳, (3) Neo4j↔PG 불일치 자동 감지 메커니즘 없음, (4) `RawDocumentStore CASCADE` → 3단계 연쇄 삭제, (5) `parent_thesis SET_NULL` 후 사이클/고아 정리 없음 |
| 🟡 Medium | 6 | (1) chainsight `news_event.duplicate_of` self FK SET_NULL 후 cluster head 손실, (2) `serverless.UserAlertConfig` SET_NULL 후 알림 메타데이터 분리, (3) `rag_analysis` 3개 SET_NULL 후 usage_log orphan, (4) `update_or_create` 호출 직후 별도 save() 호출 패턴, (5) FK to_field='symbol' 사용 시 cascade 거동, (6) 재시도 정책 `max_retries=1` 단발성 |
| 🟢 Low | 3 | (1) UniqueConstraint vs unique_together 혼용, (2) 일부 Migration에서 unique_together 제거 후 재설정, (3) DECISIONS.md에 명시된 "synced_to_neo4j 필드 금지" 원칙 일부 위반 |

**FK 사용 통계 (실측)**
- `on_delete=models.CASCADE`: **93건 / 31개 파일** (지시서 추정 37건/7파일은 부분 집계)
- `on_delete=models.SET_NULL`: **16건 / 9개 파일** (지시서 추정 7건/3파일은 부분 집계)
- `on_delete=models.PROTECT / DO_NOTHING / RESTRICT / SET_DEFAULT`: **0건** (전혀 사용하지 않음 — Critical 등급은 아니지만 보호용 FK가 전혀 없는 점은 주의)

---

## 1. FK Orphan 위험

### 1.1 SET_NULL 사용처 전수 (16건 / 9파일)

| 파일 | 라인 | FK 필드 | 참조 모델 | Orphan 정리 로직 |
|------|------|---------|----------|------------------|
| `sec_pipeline/models.py` | 86 | `SupplyChainEvidence.target_company` | `stocks.Stock` | ❌ **없음** |
| `serverless/models.py` | 660 | `*.preset` (alerts) | `ScreenerPreset` | ❌ 없음 |
| `serverless/models.py` | 808 | `*.related_thesis` (theses) | `InvestmentThesis` | ❌ 없음 |
| `serverless/models.py` | 1409 | `AdminEventLog.user` | `users.User` | ⚠️ 의도적 (감사 로그 보존) |
| `rag_analysis/models.py` | 145 | `AnalysisSession.basket` | `DataBasket` | ❌ 없음 |
| `rag_analysis/models.py` | 256 | `LLMUsageLog.session` | `AnalysisSession` | ❌ 없음 |
| `rag_analysis/models.py` | 263 | `LLMUsageLog.message` | `AnalysisMessage` | ❌ 없음 |
| `portfolio/models.py` | 327 | `*.wallet_snapshot_at_execution` | `WalletSnapshot` | ❌ 없음 |
| `portfolio/models.py` | 732 | `ChatSession.analysis_run` | `AnalysisRun` | ❌ 없음 |
| `portfolio/models.py` | 831 | `*.context_analysis_run` (decisions) | `AnalysisRun` | ❌ 없음 |
| `thesis/models/monitoring.py` | 66 | `*.indicator` | `ThesisIndicator` | ❌ 없음 |
| `thesis/models/thesis.py` | 70 | `Thesis.parent_thesis` (sources) | `Thesis` (self) | ❌ 없음 |
| `thesis/models/thesis.py` | 77 | `Thesis.copied_from` | `Thesis` (self) | ❌ 없음 |
| `thesis/models/indicator.py` | 15 | `ThesisIndicator.premise` | `ThesisPremise` | ❌ 없음 |
| `macro/models/indicators.py` | 282 | `EconomicEvent.related_indicator` | `EconomicIndicator` | ❌ 없음 |
| `chainsight/models/news_event.py` | 54 | `ChainNewsEvent.duplicate_of` | `ChainNewsEvent` (self) | ❌ 없음 |

**지시서 정정**: 보고된 "7건/3파일"은 `sec_pipeline + serverless + rag_analysis`만 카운트한 것으로 보이며, 실제로는 `portfolio`, `thesis`, `macro`, `chainsight`까지 포함하면 **16건/9파일**.

### 1.2 SET_NULL 후 Orphan 레코드 정리 — 결론: 부재

전체 코드베이스에서 다음 패턴을 검색했으나 발견되지 않음:
- `objects.filter(<set_null_field>__isnull=True).delete()`
- `cleanup_orphan*` 명령
- 정기적 cleanup Celery beat 스케줄

**유일한 orphan 정리는 Neo4j 측**: `news/services/news_neo4j_sync.py:700` — `MATCH (n:NewsEvent) WHERE NOT (n)-[]-() DELETE n` (Neo4j 그래프 전용, PG와 무관).

### 1.3 🔴 Critical: `target_company SET_NULL` 시나리오

`SupplyChainEvidence.target_company`가 `SET_NULL`로 설정되어 Stock 삭제 시 `target_company_id=NULL`이 되는데:
- `sec_pipeline/tasks.py:365`의 dirty sync는 `target_company__isnull=False` 필터로 제외하므로 **Neo4j에 영원히 동기화되지 않음**.
- `sec_pipeline/quality_checks.py:92`에서 `neo4j_dirty=True, target_company__isnull=False`만 카운트 → orphan은 **메트릭에서도 보이지 않음**.
- `target_company_name` 문자열 필드는 보존되므로 데이터 의도는 "이름만 남기고 Stock FK 분리"이지만, **재매칭 큐에 자동 등록되지 않음**.

**권장**: `signals.py`의 `post_save`에 fuzzy 매칭 결과를 다시 적용하거나 `UnmatchedCompanyQueue`에 자동 등록하는 기제 추가.

### 1.4 🟠 High: `parent_thesis / copied_from` self-FK SET_NULL

`Thesis` 모델은 `parent_thesis`(소스)와 `copied_from`(복사) 두 개의 self-FK를 가지며, 부모 삭제 시 NULL이 됨:
- 사용자가 "이 가설이 어디서 파생되었는지" 추적하는 메타데이터가 silently 손실됨.
- 사이클 검증 없음 (A→B→A self-FK 가능).

---

## 2. CASCADE 체인 분석

### 2.1 CASCADE 사용처 분포 (93건 / 31파일)

| 파일 | 건수 | 비고 |
|------|------|------|
| `portfolio/models.py` | 12 | 가장 많음. Wallet→Position, AnalysisRun→Cards/Comments 체인 |
| `graph_analysis/models.py` | 8 | Watchlist→CorrelationMatrix→PriceCache 체인 |
| `sec_pipeline/models.py` | 6 | RawDocumentStore→Evidence→Snapshot |
| `stocks/models.py` | 6 | Stock→DailyPrice/WeeklyPrice/Financials |
| `users/models.py` | 6 | User→Portfolio/Watchlist/Interest |
| `thesis/models/learning.py` | 5 | LearningGoal/Reflection 체인 |
| `rag_analysis/models.py` | 5 | Chat→Session→Message 체인 |
| `serverless/models.py` | 4 | MarketMover/Screener/CorporateAction |
| `metrics/models/benchmark.py` | 4 | Industry/PeerBenchmark |
| `thesis/models/community.py` | 4 | Thesis copy/clone 그래프 |
| `validation/*` | 9 | 모두 `stocks.Stock` 또는 `metrics.MetricDefinition` |
| `chainsight/models/*` | 10 | 11개 파일 각 1건 (Stock CASCADE) |
| 기타 | 14 | macro, news, thesis/indicator, thesis/monitoring 등 |

### 2.2 🔴 Critical: Stock 삭제 시 영향 범위

`stocks.Stock` 삭제 시 **CASCADE 또는 SET_NULL로 연쇄되는 직접 의존 테이블 ~30개** (1차 의존):

| 앱 | 모델 | on_delete | 추정 행수 영향 |
|----|------|-----------|---------------|
| stocks | DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement, StockOverviewKo, EODSignal, EODDashboardSnapshot, SignalAccuracy | CASCADE | 종목당 수천~수만 행 |
| users | Portfolio, WatchlistItem | CASCADE | 사용자 데이터 손실 |
| sec_pipeline | RawDocumentStore (CASCADE), SupplyChainEvidence×2 (source CASCADE/target SET_NULL), BusinessModelSnapshot (CASCADE) | 혼합 | 10-K 원문 + 추출 결과 전부 |
| serverless | MarketMover, ScreenerSnapshot, CorporateAction, StockKeyword, StockRelationship 등 | CASCADE | 마켓 데이터 + LLM 결과 |
| validation | CompanyMetricLatest, CompanyBenchmarkDelta, CategoryScore, ValidationNewsSummary, PeerPreset×2 | CASCADE | 1차 검증 결과 전부 |
| metrics | CompanyMetricSnapshot, PeerMetricBenchmark | CASCADE | 분기 지표 스냅샷 |
| chainsight | CompanyChainProfile, CompanyGrowthStage, CompanyCapitalDNA, CompanyInsiderSignal, CompanyEventReaction, CompanySensitivityProfile, CompanyNarrativeTag, CompanyRevenueStructure | CASCADE (각 1건) | 8개 프로파일 통째로 |
| news | NewsArticle 관련 stock FK (CASCADE) | CASCADE | 뉴스 매칭 결과 |
| portfolio | StockHolding, WalletItem 등 | CASCADE | 포트폴리오 손실 |
| thesis | (간접) ThesisIndicator → IndicatorReading | CASCADE | 가설 통제실 데이터 |

**3단계 이상 연쇄 시나리오 (실제 발생 가능)**:

```
Stock(AAPL) 삭제
  ↓ CASCADE
RawDocumentStore (10-K 원문)
  ↓ CASCADE (sec_pipeline/models.py:78)
SupplyChainEvidence (Track A 추출)        ← Neo4j 엣지와 분리됨
  ↓ CASCADE
BusinessModelSnapshot (Track B 분류)
  ↓ CASCADE (sec_pipeline/models.py:213)
BusinessModelEvidence (근거 문장)
```

```
Stock 삭제
  ↓ CASCADE
Watchlist (graph_analysis)
  ↓ CASCADE (graph_analysis/models.py:51)
StockRelationship + CorrelationMatrix
  ↓ CASCADE (graph_analysis/models.py:127)
PriceCache (그래프 분석 캐시)
```

```
Stock(AAPL) 삭제
  ↓ CASCADE
CompanyChainProfile
  ↓ (Neo4j는 stale 상태 유지) ← 동기화 미트리거
```

**Neo4j 측면의 위험**: PG에서 CASCADE로 행이 사라져도 Neo4j 엣지는 자동 삭제되지 않음. 즉, **Stock 삭제는 PG↔Neo4j 불일치를 유발하는 가장 큰 트리거**.

### 2.3 🟠 High: `RawDocumentStore` 삭제 시 3단계 연쇄

`RawDocumentStore` 자체가 삭제될 일은 거의 없으나(append-only 설계), 만약 재수집 정책으로 삭제 시:
- `SupplyChainEvidence` (CASCADE) — Neo4j 동기화 완료 여부와 무관하게 PG 행 소멸
- `BusinessModelSnapshot` (CASCADE) — `BusinessModelEvidence`까지 4단 연쇄

**완화 권장**: `RawDocumentStore`는 PROTECT로 변경 검토. 또는 archive 플래그 사용.

### 2.4 🟡 Medium: `users.User` 삭제 시 영향

`User` 삭제는 GDPR 등 사용자 요청 시 발생 가능하며:
- `users/models.py:27,171,256`: Portfolio, Watchlist, UserInterest CASCADE
- `validation/models/peer_preset.py:48`: UserPeerPreference CASCADE
- `chainsight/models/saved_path.py:22`: SavedPath CASCADE
- `serverless/models.py:1409`: AdminEventLog SET_NULL ← 감사 로그는 보존 (✅ 의도적)
- `portfolio/*`: Wallet, AnalysisRun, ChatSession 등 다단 CASCADE

**RV2-b 정책**과 관련 — 사용자 삭제 시 portfolio 다단 cascade 정합성 점검 필요.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 🔴 Critical: 동기화 플래그 3종 동시 존재 (DECISIONS 위반)

`sec_pipeline/models.py:99` 주석: `"# Neo4j 동기화 (synced_to_neo4j 필드 금지 — neo4j_dirty만 사용)"`

그러나 실제 코드베이스에는 다음 3개 필드가 혼재:

| 필드 | 사용 위치 | 의미 | 상태 |
|------|----------|------|------|
| `neo4j_dirty` (Bool) | `sec_pipeline.SupplyChainEvidence`, `chainsight.RelationConfidence` | True=동기화 필요 | ✅ 현 정책 |
| `synced_to_neo4j` (Bool) | `chainsight.RelationConfidence` (라인 130), `chainsight/tasks/relation_tasks.py` 4곳, `chainsight/services/neo4j_sync.py:49` | True=Neo4j에 반영됨 | ⚠️ 레거시 잔존 — 동시에 update |
| `neo4j_synced` (Bool) | `chainsight.CompanyChainProfile` (chain_profile.py:64), `chainsight/tasks/sync_tasks.py` 33,103,135 | False=동기화 필요 (반전 의미) | ⚠️ 별도 모델, 별도 명명 |
| `neo4j_synced_at` (DateTime) | `sec_pipeline`, `chainsight.RelationConfidence`, `chainsight.CompanyChainProfile` | 마지막 동기화 시각 | ✅ 정보성 |

**결과**:
- `RelationConfidence`는 `neo4j_dirty=False` AND `synced_to_neo4j=True`를 동시에 update해야 정상(`chainsight/services/neo4j_sync.py:47-51` 확인됨).
- `CompanyChainProfile`은 `neo4j_synced` (다른 명명) 단독 사용 — 일관성 결여.
- `chainsight/tasks/sync_tasks.py:167`은 `update(synced_to_neo4j=False, neo4j_dirty=True)` 동시 set — **2개 필드를 항상 함께 토글하는 것은 1개 필드로 통합 가능**하다는 신호.

### 3.2 동기화 실패 시 재시도 메커니즘

| Task | max_retries | 재시도 정책 |
|------|-------------|-------------|
| `sec_pipeline.sync_dirty_to_neo4j` | **1** | bind=True, 명시적 retry 호출 없음 — 단순 raise → Celery autoretry로 1회 |
| `chainsight.sync_relations_to_neo4j` | **1** | 동일 — 위임만 하고 별도 retry 없음 |
| `chainsight.sync_profiles_to_neo4j` | **1** | per-row try/except로 fail++ 카운트만 함, raise 없음 |
| `chainsight.aggregate_chain_profiles` | **1** | per-symbol try/except, exception swallow |

**문제점**:
1. `max_retries=1`은 사실상 단발성 재시도. exponential backoff 미설정 (`countdown` / `retry_backoff` 부재).
2. `sync_profiles_to_neo4j`는 행 단위 실패를 swallow + log만 → **다음 batch에도 같은 항목이 fail 반복** 가능 (모니터링 부재 시 stuck).
3. `sec_pipeline/tasks.py:411-412`의 `try/except: pass` 패턴 — DELETE 실패도 무시.
4. **CLAUDE.md `Common Bugs #25` (Celery macOS SIGSEGV)** 와 결합: macOS dev에서는 fork 직후 재시도 시 추가 크래시 위험.

**권장 (감사 결론)**:
- `retry_backoff=True, retry_backoff_max=600, retry_jitter=True` 추가
- Dead Letter Queue 또는 `sync_failure_count` 필드 도입

### 3.3 🟠 High: PG↔Neo4j 불일치 자동 감지 부재

검색 결과:
- `sec_pipeline/quality_checks.py:144` — `neo4j_synced` 카운트 (PG 측 플래그 기반) 만 보고
- `sec_pipeline/intelligence.py:97-98` — sync_synced/sync_pending 카운트 동일 패턴
- **Neo4j에 가서 실제 엣지 수와 PG 행 수를 cross-check하는 로직 없음**

즉, Neo4j 쪽 엣지가 외부에서 삭제되거나, sync 도중 일부만 반영되어도 PG의 `neo4j_dirty=False` 플래그만 보면 "정상"으로 카운트됨.

**시나리오**:
- Neo4j Aura 다운타임 중 PG 측 `neo4j_dirty=False` 처리됨 → 복구 후 엣지 누락 영구 지속.
- `sec_pipeline/tasks.py:436-444`: synced_ids에 한 번 들어가면 PG 업데이트, 단 그 사이 Neo4j commit이 부분 실패해도 감지 불가.

**권장**: 일별 reconciliation 태스크 (Neo4j COUNT vs PG `neo4j_dirty=False` COUNT 비교 + diff alert).

### 3.4 🟡 Medium: 레거시 RELATED_TO 정리 1회성 캐시

`chainsight/tasks/sync_tasks.py:158-171`의 `cleanup_key='chainsight:related_to_cleanup_v1'`는 **365일 캐시**로 1회 실행 보장.
- 캐시(Redis)가 flush되면 재실행되어 RELATED_TO 엣지 재삭제 + 모든 confirmed/probable의 dirty=True 토글.
- **CLAUDE.md `Common Bugs #27` (pytest Redis flush)**가 적용되지 않으면 prod Redis flush 시 의도치 않은 재실행 위험.

---

## 4. UniqueConstraint / update_or_create

### 4.1 unique_together / UniqueConstraint 분포

- `unique_together` 사용: **40+개 모델**에 분산
- `models.UniqueConstraint`(신식): `portfolio/models.py`에서만 5건 사용 — Django 5.x 권장 패턴
- 같은 의도가 `unique_together`(legacy)와 `UniqueConstraint`(modern)로 혼재 → **마이그레이션 일관성 부족**

대표 예:
- `users.Portfolio`: `unique_together=('user', 'stock')`
- `stocks.DailyPrice`: `unique_together=('stock', 'date')`
- `metrics.CompanyMetricSnapshot`: `unique_together=('symbol', 'fiscal_year', 'metric_code')`
- `validation.CompanyMetricSnapshot`: `unique_together=('symbol', 'fiscal_year', 'metric_code', 'preset_key')` — preset 차원 추가
- `serverless.LLMExtractedRelation`: 4-tuple unique
- `portfolio.PercentileCache`: `UniqueConstraint(metric_id, industry_code, date)`

### 4.2 🟠 High: update_or_create Race Condition (~70곳)

전체 `update_or_create` 호출: **70여 곳** (validation, serverless, chainsight, news, stocks, sec_pipeline, thesis, macro, portfolio 전체에 분산).

**Django 공식 문서 경고**:
> `update_or_create` is **not** atomic at the application level. In a race, two simultaneous calls can both pass `get` and both call `create`, then one IntegrityError is raised. The DB unique constraint is the safety net.

**위험 분류**:

| 카테고리 | 위험 등급 | 이유 |
|----------|----------|------|
| unique_together 보장 + Celery 단일 큐 | 🟢 Low | DB가 1차 방어, 중복 시 IntegrityError 흡수 가능 |
| unique_together 보장 + 다중 worker 동시 호출 | 🟡 Medium | IntegrityError 발생 시 task가 fail/retry — 멱등성은 유지되나 로그 노이즈 |
| **unique 보장 없음** | 🔴 Critical | 중복 행 생성 |

**검증 필요한 호출**:

```python
# validation/api/views.py:475 — UserPeerPreference (unique_together=('user','symbol'))
UserPeerPreference.objects.update_or_create(...)  # 🟢 보장됨

# stocks/services/stock_sync_service.py:171 — Stock (PK=symbol)
Stock.objects.update_or_create(symbol=..., defaults=...)  # 🟢 PK 보장

# serverless/tasks.py:1425 — StockRelationship
StockRelationship.objects.update_or_create(
    source_symbol=..., target_symbol=..., relationship_type=...,
)
# unique_together=('source_symbol','target_symbol','relationship_type') ✅ 보장
# 단, source_id/target_id 정규화(normalize_pair) 미적용 시 중복 가능

# sec_pipeline/tasks.py:314 — RelationConfidence
RelationConfidence.objects.update_or_create(
    symbol_a=..., symbol_b=..., relation_type=...,
)
# unique_together=('symbol_a','symbol_b','relation_type') ✅
# 단, symbol_a > symbol_b 정규화 필요 (UNDIRECTED_TYPES만)
```

**🟠 권장**: `update_or_create`는 반드시 `transaction.atomic()` 블록 안에서 호출하고 IntegrityError → retry 패턴 추가. 현재 `chainsight/services/seed_selection.py:411` 등은 atomic 미사용.

### 4.3 🟢 Low: unique_together → UniqueConstraint 마이그레이션 미완

Django 5+ 권장 패턴은 `models.UniqueConstraint`이지만, 대부분의 모델이 `unique_together`(legacy) 유지.
- `validation/migrations/0004_alter_categorysignal_unique_together_and_more.py`처럼 unique_together를 `set()`으로 비우고 다시 설정하는 패턴이 있음 → 마이그레이션 history가 노이즈.
- 향후 Django upgrade 시 deprecation warning 누적 가능.

### 4.4 🟡 Medium: `unique_together` 변경 마이그레이션의 무결성 검사 부재

`validation/migrations/0004` — `unique_together={('symbol', 'category', 'fiscal_year', 'preset_key')}` 전환 시 기존 `('symbol','category','fiscal_year')` 데이터에서 preset_key=NULL 행이 있으면 IntegrityError 가능.
- 마이그레이션 내 데이터 검증 없음.
- 신규 컬럼 default 없이 unique tuple에 포함됨.

### 4.5 self-FK + unique_together 조합 검증

- `chainsight.RelationConfidence`: `unique_together=('symbol_a', 'symbol_b', 'relation_type')` — UNDIRECTED 타입은 코드 레벨에서 정규화(`normalize_pair`) 후 저장되지만, **DB 제약은 (A,B) ≠ (B,A) 두 행 모두 허용**. 정규화를 빠뜨리는 코드 경로가 생기면 중복 발생 가능.
- `chainsight.PriceCoMovement`: `unique_together=('symbol_a','symbol_b','period')` — 동일 위험.

**권장**: `CheckConstraint(symbol_a__lte=symbol_b)` 추가로 DB 레벨 정규화 강제.

---

## 5. 종합 결론 및 우선순위

### 5.1 즉시 조치 권장 (Critical)

1. **Neo4j 동기화 플래그 통일** — DECISIONS 위반. `synced_to_neo4j`(레거시) 제거하고 `neo4j_dirty` 단일 소스로 정리. `neo4j_synced` (CompanyChainProfile)도 `neo4j_dirty`로 명명 변경.
2. **PG↔Neo4j Reconciliation Task 신설** — 일별 cross-check 후 diff > N건이면 alert. 현재 PG 플래그만 신뢰하는 구조는 silent drift 위험.
3. **`SupplyChainEvidence.target_company` orphan 자동 처리** — SET_NULL 후 `UnmatchedCompanyQueue` 자동 등록 또는 정기 fuzzy 재매칭 태스크.

### 5.2 단기 조치 권장 (High)

4. **재시도 정책 강화** — 모든 Neo4j 동기화 task에 `retry_backoff=True, retry_jitter=True, max_retries=3` 적용.
5. **`update_or_create` 호출 70곳 검토** — 다중 worker 환경에서 unique 보장 여부 audit. 미보장 케이스에 unique 제약 추가.
6. **Stock CASCADE 영향 매트릭스 문서화** — Stock 삭제는 사실상 hard delete 불가능. soft delete 플래그(`is_active=False`) 도입 또는 PROTECT로 변경 검토.

### 5.3 중기 조치 권장 (Medium)

7. **`RawDocumentStore` PROTECT 검토** — 10-K 원문은 append-only이므로 PROTECT가 의미적으로 적합.
8. **chainsight UNDIRECTED 정규화 DB 제약** — `CheckConstraint(symbol_a__lte=symbol_b)` 추가.
9. **`unique_together` → `UniqueConstraint` 점진적 마이그레이션** — 신규 모델은 `UniqueConstraint`만 사용.

### 5.4 데이터 무결성 종합 점수

| 영역 | 점수 (10점 만점) | 주요 감점 |
|------|----------------|----------|
| FK 설계 | 6/10 | PROTECT 미사용, SET_NULL orphan 정리 부재 |
| CASCADE 안전성 | 5/10 | Stock 단일 행 삭제가 30+ 테이블 영향 |
| Neo4j 동기화 | 4/10 | 플래그 3종 혼재, reconciliation 부재, 재시도 약함 |
| Unique 제약 | 7/10 | unique_together 광범위 적용, race window는 일부 존재 |
| **종합** | **5.5/10** | Critical 3건 해소 시 7.5/10 도달 가능 |

---

**감사자 노트**: 본 보고서는 정적 분석 기반이며, 실제 prod DB의 orphan 행 수나 Neo4j↔PG diff 실측치는 별도 운영 쿼리로 확인이 필요합니다. 본 감사에서는 코드 수정을 일절 수행하지 않았습니다.
