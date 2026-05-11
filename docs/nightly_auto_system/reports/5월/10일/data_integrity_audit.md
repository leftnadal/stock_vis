# 데이터 무결성 감사 보고서

**작성일**: 2026-05-10
**범위**: stock_vis 백엔드 18개 앱 (stocks, users, news, serverless, rag_analysis, sec_pipeline, graph_analysis, chainsight, macro, marketpulse, metrics, portfolio, thesis, validation, ...)
**감사 모드**: 읽기 전용 (코드 수정 없음)

---

## 요약 (위험도별 이슈 수)

> 사전 카운트 보정: 사용자 제시 카운트(SET_NULL 7/3, CASCADE 37/7)는 `models*.py`만 한정한 결과.
> 실제 모델 레이아웃은 `models/` 패키지가 다수(macro, marketpulse, metrics, thesis, chainsight, validation)이며 `models.py` glob에 포함되지 않음.
> **실측치**: SET_NULL 17곳/11파일, CASCADE ~93곳/18파일.

| 위험도 | 개수 | 핵심 항목 |
|--------|------|---------|
| 🔴 HIGH | 4 | Stock CASCADE 단일 실패점 / SET_NULL orphan 정리 부재 (rag_analysis, sec_pipeline) / update_or_create + transaction.atomic 미결합 / Neo4j 자동 재시도 약함 (max_retries=1~2, backoff 없음) |
| 🟡 MEDIUM | 5 | PG↔Neo4j 양방향 무결성 검증 없음 / SET_NULL FK 의미가 NULL 비호환인 곳 다수 / 레거시 `synced_to_neo4j` 흔적 잔존 / SupplyChainEvidence orphan 재매칭만 있고 정리 없음 / Celery `default_retry_delay=60s` 고정 (exponential backoff 없음) |
| 🟢 LOW | 3 | PROTECT 사용 7곳 — 명시적 액션 보호로 안전 / unique_together·UniqueConstraint 광범위 적용 / chainsight `neo4j_dirty` 단일 소스 통일 완료 (audit P0 #9) |

---

## FK orphan 위험

### SET_NULL 사용처 (17곳, 11파일 — 실측)

| # | 위치 | FK | nullable 의미 | 위험도 |
|---|------|----|-|-|
| 1 | `rag_analysis/models.py:145` | AnalysisSession.basket → DataBasket | basket 삭제 후 세션 분석 컨텍스트 유실 | 🔴 HIGH |
| 2 | `rag_analysis/models.py:256` | LLMUsageLog.session | 세션 삭제 후 비용 추적 끊김 | 🟡 MEDIUM |
| 3 | `rag_analysis/models.py:263` | LLMUsageLog.message | 메시지 삭제 후 토큰 회계 끊김 | 🟡 MEDIUM |
| 4 | `serverless/models.py:660` | ScreenerAlert.preset | "프리셋 기반 알림" 삭제 시 커스텀 필터로 강등 (의도된 동작) | 🟢 LOW |
| 5 | `serverless/models.py:808` | InvestmentThesis.user | 사용자 탈퇴 후 익명 테제 보존 (의도된 동작) | 🟢 LOW |
| 6 | `serverless/models.py:1409` | AdminAuditLog.user | 감사 추적용 (의도된 동작) | 🟢 LOW |
| 7 | `chainsight/models/news_event.py:54` | ChainNewsEvent.duplicate_of (self FK) | 중복 원본 삭제 시 dup 플래그만 남음 | 🟡 MEDIUM |
| 8 | `macro/models/indicators.py:298` | EconomicIndicatorSeries.related_indicator | 자기 참조성 메타데이터 | 🟢 LOW |
| 9 | `portfolio/models.py:327` | AnalysisRun.wallet_snapshot_at_execution | 스냅샷 삭제 후 시점 컨텍스트 유실 | 🟡 MEDIUM |
| 10 | `portfolio/models.py:732` | ChatSession.analysis_run | 분석 실행 삭제 후 채팅 분리 (의도) | 🟢 LOW |
| 11 | `portfolio/models.py:831` | UserDecision.context_analysis_run | 결정 시점 분석 컨텍스트 유실 | 🟡 MEDIUM |
| 12 | `thesis/models/monitoring.py:66` | MonitoringSnapshot.indicator | 지표 삭제 후 스냅샷 분리 | 🟡 MEDIUM |
| 13 | `thesis/models/indicator.py:15` | ThesisIndicator.premise | premise 없이 지표 고아 가능 | 🟡 MEDIUM |
| 14 | `thesis/models/thesis.py:70` | Thesis.source_news | 뉴스 삭제 후 출처 유실 (의도) | 🟢 LOW |
| 15 | `thesis/models/thesis.py:77` | Thesis.copied_from (self) | 원본 가설 삭제 후 복제본 보존 (의도) | 🟢 LOW |
| 16 | `sec_pipeline/models.py:86` | **SupplyChainEvidence.target_company** | **매칭 미해결 evidence가 잔존** | 🔴 HIGH |
| 17 | `marketpulse/models/anomaly.py:25` | Anomaly.paired_news | 뉴스 삭제 후 anomaly 보존 | 🟢 LOW |

### SET_NULL 후 orphan 정리 로직

전 코드베이스에서 발견된 orphan 처리 로직:

- ✅ `news/services/news_neo4j_sync.py:700-711` — Neo4j 측 orphaned `NewsEvent` 노드 정리 (정기)
- ✅ `sec_pipeline/management/commands/rematch_unmatched.py` — `target_company__isnull=True` 재매칭 (수동 명령)
- ✅ `sec_pipeline/signals.py:44-58` — UnmatchedCompanyQueue 해소 시 evidence 일괄 매칭
- ❌ **나머지 15개 SET_NULL 사용처에는 정리 로직 없음**

**🔴 HIGH 권장**:
- `rag_analysis/AnalysisSession.basket=NULL` 상태 — 분석 컨텍스트가 비어버린 세션이 영구 누적됨. 정기 cleanup task 또는 `basket IS NULL AND messages_count=0` 조건 archival 필요.
- `sec_pipeline/SupplyChainEvidence.target_company=NULL` 적체 — `quality_checks.py`에 `unmatched > 100` 알림은 있으나 자동 archival 없음. 90일 이상 미매칭 evidence는 cold storage 이동 권장.

---

## CASCADE 체인

### Stock 직접 참조 (CASCADE 17곳)

`stocks.Stock`을 CASCADE로 참조하는 모델:

```
stocks/models.py     : DailyPrice, WeeklyPrice, StockOverviewKO, StockFinancials,
                       StockEarnings, EODSignal, EODDashboardSnapshot
users/models.py      : Portfolio, WatchlistItem
chainsight/models/   : CompanyChainProfile, CompanyNarrativeTag, CompanySensitivity,
                       CompanyGrowthStage, CompanyEventReaction, CompanyCapitalDNA,
                       CompanyRevenueStructure, CompanyInsiderSignal, ChainNewsEvent (PROTECT)
sec_pipeline/models  : RawDocumentStore, SupplyChainEvidence(source), BusinessModelSnapshot
validation/models/   : CompanyMetricLatest, CategoryScore, CompanyBenchmarkDelta,
                       PeerPreset, UserPeerPreference, ValidationNewsSummary
graph_analysis/models: StockCorrelationData (NOT NULL CASCADE)
metrics/models/      : CompanyMetricSnapshot
portfolio/models.py  : DiagnosticCard.target_stock (PROTECT — 안전)
news/models.py       : NewsArticleSymbol (M2M through)
```

### 3단계 이상 연쇄 삭제 (대표 체인)

**Chain A — Stock 삭제 시 portfolio 도미노**
```
Stock
  ├─→ Portfolio (CASCADE)            [users/models.py:28]
  │     └─→ AnalysisRun (CASCADE)    [portfolio/models.py:54]
  │           ├─→ DiagnosticCard (CASCADE)   [portfolio/models.py:483]
  │           ├─→ MetricResult (CASCADE)     [portfolio/models.py:388]
  │           ├─→ MetricComment (CASCADE)    [portfolio/models.py:561]
  │           └─→ ChatSession (SET_NULL)     [portfolio/models.py:732]
  │                 └─→ ChatMessage (CASCADE) [portfolio/models.py:772]
```
→ Stock 1건 삭제 시 **6단계** 연쇄, 사용자 분석 이력 전부 소실.

**Chain B — Watchlist 도미노**
```
User (delete)
  └─→ Watchlist (CASCADE)              [users/models.py:171]
        └─→ WatchlistItem (CASCADE)    [users/models.py:197]
              └─→ (graph_analysis StockCorrelationData FK to WatchlistStock) [graph_analysis/models.py]
```

**Chain C — sec_pipeline 도미노**
```
RawDocumentStore (delete)
  ├─→ SupplyChainEvidence (CASCADE)  [sec_pipeline/models.py:78]
  └─→ BusinessModelSnapshot (CASCADE) [sec_pipeline/models.py:165]
        └─→ BusinessModelEvidence (CASCADE) [sec_pipeline/models.py:213]
```

**Chain D — Thesis 도미노**
```
Thesis (delete)
  ├─→ ThesisPremise (CASCADE)        [thesis/models/thesis.py:146]
  │     └─→ ThesisIndicator (SET_NULL on premise) [thesis/models/indicator.py:15]
  ├─→ ThesisSnapshot (CASCADE)       [thesis/models/monitoring.py:10]
  ├─→ ThesisAlertRule (CASCADE)
  ├─→ ThesisLearning (CASCADE)       [thesis/models/learning.py:74]
  └─→ ThesisCommunity (CASCADE)      [thesis/models/community.py]
```

### Stock 삭제 영향 범위 (정량)

| 영역 | 삭제될 행 추정 | 비고 |
|------|------|------|
| 가격 데이터 (DailyPrice, WeeklyPrice) | ~5,000+ rows / symbol | 5년치 누적 |
| 재무 (StockFinancials, StockEarnings) | ~20+ rows / symbol | 분기별 |
| Chain Sight 프로파일 (10개 모델) | ~10 rows / symbol | OneToOne/ForeignKey 혼재 |
| validation (5개 모델) | ~수십 rows / symbol | metric x preset 조합 |
| portfolio/AnalysisRun (간접) | 사용자 수 × 분석 횟수 | 6단계 도미노 |
| sec_pipeline (RawDoc, Evidence, BMS) | 10-K 수 × evidence 수 | source FK는 CASCADE |
| 사용자 데이터 (Portfolio, WatchlistItem) | 사용자 수 만큼 | **사용자 손실** |

**🔴 HIGH 권장**:
- `stocks.Stock` 삭제는 **사실상 비가역적 데이터 손실**. 심볼 변경(예: FB→META) 시나리오에서 위험.
- 권장: `Stock.is_active=False` 소프트 삭제 + `delisted_at` 도입, 물리 삭제는 admin 이중 확인 필요.
- 차선책: `DiagnosticCard.target_stock`처럼 **PROTECT** 채택을 핵심 사용자 데이터 (`Portfolio`, `WatchlistItem`)에 확대.

### 추가 관찰

- `ChainNewsEvent.symbol` (PROTECT) — Stock 삭제 차단 ✅
- `MetricResult.target_stock` 등 `portfolio/`의 PROTECT 4곳 — 아키텍처상 가장 보수적인 영역 (의도된 안전).

---

## Neo4j 동기화

### neo4j_dirty 패턴 사용 현황

✅ **단일 소스 통일 완료** — `chainsight/migrations/0008_unify_neo4j_flags.py` (audit P0 #9, 2026-04-29):

| 모델 | 필드 | 의미 |
|------|------|------|
| `chainsight.CompanyChainProfile` | `neo4j_dirty` (BooleanField, default=True, db_index=True) | True = 동기화 필요 |
| `chainsight.RelationConfidence` | `neo4j_dirty` (db_index=True) | True = 동기화 필요 |
| `sec_pipeline.SupplyChainEvidence` | `neo4j_dirty` (default=True, indexed) | True = 동기화 필요 |

`save()` 자동 토글:
- `chainsight/models/relation_discovery.py:157-158` — `save()` 오버라이드로 `neo4j_dirty=True` 자동 세팅
- `update_or_create()` 호출 시 → `save()` 발화 → `neo4j_dirty=True` 자동
- `queryset.update(...)` 사용 시 → `save()` 미발화 → **수동 토글 필요** (`relation_tasks.py:382-402` 명시적 처리됨)

### 동기화 실패 시 재시도 메커니즘

| 태스크 | max_retries | retry_delay | exponential backoff | 위험도 |
|--------|-|-|-|-|
| `chainsight-neo4j-dirty-sync` (`neo4j_dirty_sync_tasks.py:14`) | 2 | 60s 고정 | ❌ 없음 | 🟡 MEDIUM |
| `sync_dirty_to_neo4j` (`sec_pipeline/tasks.py:337`) | 1 | 기본값 | ❌ 없음 | 🟡 MEDIUM |
| `sync_profiles_to_neo4j` (`chainsight/tasks/sync_tasks.py:97`) | 1 | 기본값 | ❌ 없음 | 🟡 MEDIUM |
| `sync_relations_to_neo4j` (`chainsight/tasks/sync_tasks.py:148`) | 1 | 기본값 | ❌ 없음 | 🟡 MEDIUM |

**복구 메커니즘**: 실패한 row는 `neo4j_dirty=True`로 남아 다음 주기에 재시도 (cron 기반 자가 회복). 무한 재시도 방지 장치 없음 → 영구 실패 row가 dirty queue 적체.

`sync_dirty_to_neo4j`는 2-Phase 패턴 (`select_for_update(skip_locked=True)` + Phase B에서 개별 row try/except) — 단일 row 실패가 배치 전체를 막지 않는 안전 설계 ✅.

### PG ↔ Neo4j 불일치 감지

✅ **PG → Neo4j 적체 감지** (`sec_pipeline/quality_checks.py:90-97`):
```python
dirty_count = SupplyChainEvidence.objects.filter(
    neo4j_dirty=True, target_company__isnull=False
).count()
if dirty_count > 50:
    alerts.append(f"⚠️ Neo4j dirty 적체 {dirty_count}건 — 50건 초과")
```

✅ **Neo4j orphan 정리** (`news/services/news_neo4j_sync.py:700-711`):
```cypher
MATCH (n:NewsEvent) WHERE NOT (n)<-[:HAS_EVENT]-()
DELETE n
```

❌ **불일치 (Mismatch) 감지 부재**:
- "PG에는 있는데 Neo4j에는 없는" 노드/엣지 정합성 비교 로직 없음
- "Neo4j에는 있는데 PG에는 없는" 좀비 엣지 탐지 로직 없음 (NewsEvent 외)
- `neo4j_dirty=False` 표시되었지만 Neo4j 측 INSERT가 실제 누락된 케이스 검증 없음 (Phase B `repo.run_query()` 예외만 잡고 정상 응답은 검증 안 함)

**🔴 HIGH 권장**:
- 주간 `audit_neo4j_consistency.py` 배치 추가 — PG 카운트 vs `MATCH (n:Stock) RETURN count(n)` 비교
- `neo4j_dirty=False` 행 샘플링 검증 (e.g., 1% 샘플 → Neo4j 존재 확인)
- 영구 실패 row 마킹 (`neo4j_dirty=True` 30일 이상 → `neo4j_dead_letter=True` 격리)

### 잔존 레거시

- `chainsight/migrations/0004_companychainprofile_neo4j_synced_and_more.py` — `neo4j_synced` (반전 의미) 잔존, 0008에서 `neo4j_dirty`로 통일
- `sec_pipeline/quality_checks.py:144` — 카운터 키 `'neo4j_synced'` (의미상 `neo4j_dirty=False`) — 외부 모니터링이 이 키 사용 시 의미 혼동 주의

---

## Unique 제약조건

### unique_together 현황 (대표)

| 앱 | 모델 | 제약 |
|----|------|------|
| stocks | DailyPrice, WeeklyPrice, EODDashboardSnapshot | `(stock, date)` |
| stocks | StockFinancials, StockEarnings, ... | `(stock, period_type, fiscal_year, fiscal_quarter)` |
| stocks | EODSignal | `(stock, signal_date, signal_tag)` |
| users | Portfolio, WatchlistItem, Watchlist, UserInterest | `(user, stock)`, `(user, name)`, `(watchlist, stock)`, `(user, interest_type, value)` |
| serverless | EnhancedScreenerSnapshot, KeywordSnapshot, MoverSnapshot, ETFHolding 등 | 일자별 스냅샷 보호 (10+ 제약) |
| validation | CompanyMetricLatest, CategoryScore, BenchmarkDelta, PeerPreset, UserPeerPreference | `(symbol, ...preset_key)` 등 |
| chainsight | RelationConfidence (3 변형), CompanyEventReaction, ChainNewsEvent | 관계 중복 방지 |
| metrics | CompanyMetricSnapshot, IndustryMetricBenchmark, PeerMetricBenchmark | `(symbol, fiscal_year, metric_code, ...)` |
| thesis | ThesisSnapshot, ThesisIndicator, KeywordCache, ThesisCommunity | 시계열·중복 방지 |
| portfolio | WalletItem, PercentileCache, MetricResult, DiagnosticCard, MetricComment | UniqueConstraint (4건) |
| sec_pipeline | CompanyAlias | `(alias, context_sector)` |
| graph_analysis | 상관관계 캐시, 그래프 스냅샷 | `(watchlist, stock_a, stock_b, date)` 등 |
| marketpulse | MarketRegime, MarketBriefing, ... | 일자/유저 중복 방지 |
| news | NewsArticleSymbol, KeywordSnapshot | `(news, symbol)`, `(symbol, date)` |
| macro | EconomicIndicatorValue, MacroIndexValue, MacroRelation | `(indicator, date)` 등 |
| rag_analysis | BasketItem | `(basket, item_type, reference_id)` |

→ 중복 방지가 **광범위하게 적용**. 🟢 LOW.

### update_or_create 사용 시 race condition 가능성

`update_or_create` 발견 파일: **63개**.

**Django ORM 안전성**: `update_or_create`는 내부적으로 `select_for_update`를 쓰지 않음. 동시 호출 시 IntegrityError 발생 후 자동 재시도하나, 그 전에 두 트랜잭션이 `get()`에서 동시에 None을 받으면 race가 가능.

**검증**: `transaction.atomic`과 함께 쓰는 곳 21개 파일.

| 파일 | atomic+update_or_create 결합 여부 |
|------|----|
| `sec_pipeline/tasks.py` | ✅ 결합 (`with transaction.atomic():` 블록 내부) |
| `chainsight/tasks/relation_tasks.py` | ⚠️ 일부만 — line 291 update_or_create 직접 호출 (atomic 블록 외부) |
| `serverless/services/data_sync.py` | ❌ atomic 미사용 |
| `news/tasks.py` | ❌ 다수의 update_or_create가 atomic 외부 |
| `validation/services/relative_metrics.py` | ❌ atomic 미사용 |
| `chainsight/services/recheck_service.py` | ✅ 결합 |
| `validation/api/views.py` | ✅ 결합 |
| `users/views.py` | ✅ 결합 |

**🔴 HIGH 권장**:
- `news/tasks.py`, `validation/services/*` — Celery beat 동시 실행 시 race window 존재. `unique_together`가 백업하므로 **데이터 중복은 막히지만 IntegrityError 예외**가 발생 → 태스크 재시도 폭주 가능.
- 패턴: `with transaction.atomic(): obj, created = Model.objects.select_for_update().update_or_create(...)` 권장 (또는 PostgreSQL `ON CONFLICT` for bulk).
- 참고: Django docs는 `update_or_create`가 race-safe하지 않다고 명시 (https://docs.djangoproject.com/en/5.1/ref/models/querysets/#update-or-create).

### PROTECT 사용 (안전한 영역)

| 위치 | 의미 |
|------|------|
| `metrics/models/metric_snapshot.py:11` | MetricSnapshot.metric_definition — 정의 삭제 차단 |
| `chainsight/models/news_event.py:23` | ChainNewsEvent.symbol — Stock 보호 |
| `portfolio/models.py:90, 393, 495, 566` | Wallet, AnalysisRun, MetricResult, DiagnosticCard → Stock | 사용자 분석 데이터 보호 |
| `marketpulse/models/snapshot.py:51` | MarketBriefing.indicator | 지표 삭제 차단 |

→ 모두 **명시적 사용자 액션 보호**. 🟢 LOW.

---

## 핵심 권장 조치 (우선순위)

1. **[🔴 P0]** `Stock` 모델 소프트 삭제 패턴 도입 (`is_active`, `delisted_at`) — Watchlist/Portfolio/AnalysisRun 등 **사용자 분석 이력 영구 손실** 방어.
2. **[🔴 P0]** `update_or_create` 사용 핫스팟(`news/tasks.py`, `validation/services/*`) `transaction.atomic` + `select_for_update` 결합 — Celery 동시 실행 시 IntegrityError 폭주 방지.
3. **[🔴 P0]** Neo4j 동기화 실패 dead-letter 격리 — `neo4j_dirty=True` 30일 초과 row 자동 마킹, 영구 실패 row가 dirty queue 적체 방지.
4. **[🟡 P1]** PG↔Neo4j 양방향 정합성 batch (주간) — `Stock` 카운트, `RelationConfidence vs (a)-[r]-(b)` 비교, drift 알림.
5. **[🟡 P1]** `rag_analysis.AnalysisSession.basket=NULL` 적체 cleanup — 90일 무활동 + basket NULL → archival.
6. **[🟡 P1]** `sec_pipeline.SupplyChainEvidence` orphan 정책 — 90일 미매칭 evidence cold storage.
7. **[🟡 P2]** Celery sync 태스크 `retry_backoff=True, retry_backoff_max=600` 추가 — 일시적 Neo4j 장애 회복력.
8. **[🟢 P3]** `quality_checks.py:144` 카운터 키 명칭 정리 (`neo4j_synced` → `neo4j_synced_count`) — 외부 모니터링 의미 혼동 제거.

---

**감사 종료**. 코드 수정 없음 (읽기 전용).
