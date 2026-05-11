# 데이터 무결성 감사 보고서

**감사일**: 2026-04-14
**감사 범위**: 전체 Django 앱 18개, models*.py 파일 (migrations 제외)
**브랜치**: data_structure_remodeling_V1

---

## 요약

| 위험도 | 이슈 수 | 주요 항목 |
|--------|---------|----------|
| **CRITICAL** | 3 | Stock 삭제 시 27+ 테이블 연쇄 삭제, User 삭제 시 4단계 CASCADE 체인, update_or_create 75+ 곳 중 70%가 atomic 미적용 |
| **HIGH** | 5 | SEC 파이프라인 3단계 CASCADE, Neo4j drift 감지 부재, orphan 정리 로직 부재 (5개 모델), MarketBreadth unique 미설정, 뉴스 Neo4j TTL 자동 정리 미구현 |
| **MEDIUM** | 6 | SET_NULL orphan 누적 (AnalysisSession/UsageLog), neo4j_dirty vs neo4j_synced 패턴 불일치, IntegrityError 미처리 70+ 곳, 암묵적 OneToOne uniqueness, 뉴스 sync 상태 필드 부재, SEC DELETE+CREATE 패턴 비원자성 |
| **LOW** | 4 | 자기참조 SET_NULL (Thesis.copied_from 등), 감사 로그 orphan (AdminActionLog), schema verify 미자동화, KB driver 별도 인스턴스 |

**총 이슈: 18건**

---

## 1. FK Orphan 위험

### 1.1 SET_NULL 사용 현황 (13곳)

| # | 파일 | 모델.필드 | 참조 모델 | null/blank | 위험도 |
|---|------|-----------|----------|------------|--------|
| 1 | `serverless/models.py:660` | ScreenerAlert.preset | ScreenerPreset | null=True, blank=True | LOW |
| 2 | `serverless/models.py:808` | InvestmentThesis.user | users.User | null=True, blank=True | LOW |
| 3 | `serverless/models.py:1409` | AdminActionLog.user | users.User | null=True | LOW |
| 4 | `sec_pipeline/models.py:86` | SupplyChainEvidence.target_company | stocks.Stock | null=True, blank=True | MEDIUM |
| 5 | `macro/models/indicators.py:282` | EconomicEvent.related_indicator | EconomicIndicator | null=True, blank=True | LOW |
| 6 | `thesis/models/indicator.py:15` | ThesisIndicator.premise | ThesisPremise | null=True, blank=True | LOW |
| 7 | `thesis/models/thesis.py:70` | Thesis.source_news | news.NewsArticle | null=True, blank=True | MEDIUM |
| 8 | `thesis/models/thesis.py:77` | Thesis.copied_from | self (Thesis) | null=True, blank=True | LOW |
| 9 | `thesis/models/monitoring.py:66` | ThesisAlert.indicator | ThesisIndicator | null=True, blank=True | LOW |
| 10 | `rag_analysis/models.py:145` | AnalysisSession.basket | DataBasket | null=True | MEDIUM |
| 11 | `rag_analysis/models.py:256` | UsageLog.session | AnalysisSession | null=True, blank=True | MEDIUM |
| 12 | `rag_analysis/models.py:263` | UsageLog.message | AnalysisMessage | null=True, blank=True | MEDIUM |
| 13 | `chainsight/models/news_event.py:54` | ChainNewsEvent.duplicate_of | self | null=True, blank=True | LOW |

> `SET_DEFAULT`, `DO_NOTHING` 사용: **없음** (양호)

### 1.2 Orphan 정리 메커니즘 현황

| 모델 | 정리 로직 | 상태 |
|------|----------|------|
| AnalysisSession (basket=NULL) | 없음 | **미구현** |
| UsageLog (session=NULL) | 없음 | **미구현** |
| UsageLog (message=NULL) | 없음 | **미구현** |
| SupplyChainEvidence (target_company=NULL) | `sec_pipeline/signals.py` — UnmatchedCompanyQueue 해소 시 재매칭 | 부분 구현 |
| Thesis (source_news=NULL) | 없음 | **미구현** (가설 자체는 유효하므로 저위험) |

**기존 정리 태스크** (orphan 전용은 아님):
- `config/tasks.py` — `cleanup_old_task_results()`: TaskResult 30/90일 만료 삭제
- `serverless/tasks.py` — `cleanup_expired_category_cache()`: CategoryCache 만료 삭제
- `serverless/tasks.py` — `cleanup_expired_llm_relations()`: LLMExtractedRelation 만료 삭제
- `sec_pipeline/management/commands/rematch_unmatched.py`: 미매칭 기업 재시도

**핵심 Gap**: FK가 NULL로 설정된 후 orphan 레코드를 주기적으로 탐지/정리하는 범용 메커니즘이 없음. 특히 `rag_analysis` 앱의 UsageLog는 과금/감사 용도로 orphan 누적이 데이터 품질에 직접 영향.

---

## 2. CASCADE 체인 분석

### 2.1 CASCADE 사용 현황 (86곳, 18개 앱)

| 앱 | CASCADE FK 수 | 주요 참조 대상 |
|----|-------------|--------------|
| stocks | 5+ | Stock |
| users | 6 | User, Stock, Watchlist |
| thesis | 13 | User, Thesis, ThesisIndicator |
| serverless | 15+ | Stock, ScreenerPreset |
| validation | 9 | Stock, MetricDefinition, User |
| sec_pipeline | 5 | Stock, RawDocumentStore |
| graph_analysis | 8 | Watchlist, Stock, CorrelationEdge |
| rag_analysis | 5 | User, DataBasket, AnalysisSession |
| chainsight | 6 | Stock (OneToOne) |
| metrics | 4+ | Stock, MetricDefinition |
| macro | 2 | EconomicIndicator |
| news | 2 | NewsArticle |

### 2.2 3단계 이상 연쇄 삭제 체인

#### CRITICAL: User 삭제 — 4단계 체인

```
User ─┬→ Thesis ─┬→ ThesisPremise
      │          ├→ ThesisIndicator ─┬→ IndicatorReading   ← 4단계
      │          │                   └→ ValidityRecord     ← 4단계
      │          ├→ ThesisSnapshot
      │          ├→ ThesisAlert
      │          └→ PopularThesisCache
      ├→ Watchlist ─→ WatchlistItem                        ← 3단계
      ├→ Portfolio
      ├→ UserInterest
      ├→ UserPeerPreference
      ├→ DataBasket ─→ BasketItem                          ← 3단계
      ├→ AnalysisSession ─→ AnalysisMessage                ← 3단계
      ├→ HypothesisEvent
      ├→ InvestorDNA (OneToOne)
      └→ ThesisFollow
```

**영향**: User 1명 삭제 시 10+ 직접 테이블 + 15+ 간접 테이블에서 레코드 삭제. **Soft delete 미구현**이므로 복구 불가.

#### CRITICAL: Stock 삭제 — 27+ 테이블 영향

```
Stock ─┬→ DailyPrice, WeeklyPrice                          (stocks)
       ├→ BalanceSheet, IncomeStatement, CashFlowStatement  (stocks)
       ├→ StockOverviewKo                                   (stocks)
       ├→ Portfolio, WatchlistItem                          (users)
       ├→ RawDocumentStore ─→ SupplyChainEvidence           ← 3단계 (sec_pipeline)
       ├→ BusinessModelSnapshot ─→ BusinessModelEvidence    ← 3단계 (sec_pipeline)
       ├→ CorrelationEdge ─→ CorrelationAnomaly             ← 3단계 (graph_analysis)
       ├→ CompanyChainProfile (OneToOne)                    (chainsight)
       ├→ CompanyInsiderSignal (OneToOne)                   (chainsight)
       ├→ CompanyRevenueStructure (OneToOne)                (chainsight)
       ├→ CompanyCapitalDNA (OneToOne)                      (chainsight)
       ├→ CompanyEventReaction (OneToOne)                   (chainsight)
       ├→ CompanyGrowthStage (OneToOne)                     (chainsight)
       ├→ CompanyBenchmarkDelta, CompanyMetricLatest        (validation)
       ├→ CategorySignal, PeerPreset, UserPeerPreference    (validation)
       ├→ ValidationNewsSummary                             (validation)
       ├→ PeerMetricBenchmark, PeerListCache                (metrics)
       └→ CompanyMetricSnapshot (PROTECT — 유일한 방어)      (metrics)
```

**주의**: `CompanyMetricSnapshot`만 `on_delete=PROTECT`를 사용. 이 레코드가 존재하면 Stock 삭제가 차단됨. 나머지 26+ 테이블은 모두 무조건 연쇄 삭제.

#### HIGH: SEC Pipeline — 3단계 체인

```
Stock → RawDocumentStore → SupplyChainEvidence    (sec_pipeline/models.py:25→78)
Stock → BusinessModelSnapshot → BusinessModelEvidence  (sec_pipeline/models.py:161→165)
```

SEC 10-K 분석 데이터 전체가 Stock 삭제와 함께 소실. 복구 불가.

#### MEDIUM: Watchlist → Graph Analysis — 3단계 체인

```
Watchlist → CorrelationMatrix
          → CorrelationEdge → CorrelationAnomaly
```

### 2.3 위험 평가

| 체인 | 깊이 | 위험도 | 근거 |
|------|------|--------|------|
| User → Thesis → ThesisIndicator → IndicatorReading | 4 | CRITICAL | 사용자 생성 분석 데이터 영구 소실 |
| Stock → 27+ 테이블 | 1-3 | CRITICAL | 전체 종목 데이터 소실, Neo4j와 불일치 발생 |
| Stock → RawDocumentStore → SupplyChainEvidence | 3 | HIGH | SEC 수집 데이터 복구 불가 |
| Stock → BusinessModelSnapshot → BusinessModelEvidence | 3 | HIGH | 사업모델 분석 복구 불가 |
| User → DataBasket → BasketItem | 3 | MEDIUM | RAG 분석 맥락 소실 |
| Watchlist → CorrelationEdge → CorrelationAnomaly | 3 | MEDIUM | 상관관계 분석 소실 |

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 Dirty Flag 현황

| 모델 | 플래그 | 위치 | 자동 설정 | 인덱스 |
|------|--------|------|----------|--------|
| SupplyChainEvidence | `neo4j_dirty` | sec_pipeline/models.py:100 | default=True | db_index (Line 111) |
| RelationConfidence | `neo4j_dirty` | chainsight/models/relation_discovery.py:131 | save() 오버라이드에서 True | db_index (Line 145) |
| RelationConfidence | `synced_to_neo4j` | chainsight/models/relation_discovery.py:130 | default=False | 없음 |
| CompanyChainProfile | `neo4j_synced` | chainsight/models/chain_profile.py:64 | default=False | db_index |

**패턴 불일치 (MEDIUM)**:
- `sec_pipeline`: `neo4j_dirty` 단독 사용 (코드 주석에서 `synced_to_neo4j` 사용 금지 명시)
- `chainsight/RelationConfidence`: `neo4j_dirty` + `synced_to_neo4j` 이중 사용
- `chainsight/CompanyChainProfile`: `neo4j_synced` (반대 의미, dirty 아닌 synced)
- `news/NewsArticle`: **동기화 상태 필드 없음** — Neo4j 기존 노드 조회로 중복 방지

### 3.2 동기화 Celery 태스크

| 태스크 | 위치 | max_retries | timeout | 동기화 방식 |
|--------|------|-------------|---------|------------|
| `sync_dirty_to_neo4j` | sec_pipeline/tasks.py:337 | 1 | 300s/360s | DELETE + CREATE (비 MERGE) |
| `run_neo4j_dirty_sync` | chainsight/tasks/neo4j_dirty_sync_tasks.py:14 | 2 | N/A | MERGE (서비스 위임) |
| `sync_profiles_to_neo4j` | chainsight/tasks/sync_tasks.py:96 | 1 | 1800s/1860s | MATCH SET |
| `sync_relations_to_neo4j` | chainsight/tasks/sync_tasks.py:147 | 1 | 1800s/1860s | dirty sync 위임 + 레거시 정리 |
| `sync_news_to_neo4j` | news/tasks.py:588 | 2 | 3600s/3660s | MERGE (서비스 위임) |

### 3.3 동기화 실패 시 재시도 메커니즘

| 영역 | 에러 처리 | 평가 |
|------|----------|------|
| SEC Pipeline DELETE 단계 | `except Exception: pass` (sec_pipeline/tasks.py:406-411) | **위험** — 실패 무시 |
| SEC Pipeline CREATE 단계 | 레코드별 로깅, PG 업데이트 건너뜀 (tasks.py:436-437) | 양호 — dirty 유지로 재시도 |
| ChainSight dirty sync | 레코드별 try/except, 실패 시 PG 미업데이트 (neo4j_sync.py:42-43) | 양호 — dirty 유지로 재시도 |
| ChainSight profile sync | 레코드별 try/except (sync_tasks.py:136-139) | 양호 |
| News sync | Neo4j 미가용 시 graceful return (tasks.py:607-609) | **주의** — 동기화 포기 |
| Graph Repository | `GraphQueryError` 래핑 (repository.py:136-137) | 양호 — 에러 추적 가능 |

### 3.4 불일치 감지 방법

**구현된 것**:
- `sec_pipeline/quality_checks.py:92-97` — dirty backlog 50건 초과 시 경고
- `sec_pipeline/intelligence.py:87-99` — sync_synced/sync_pending 카운트
- `chainsight/graph/schema.py:50-64` — Neo4j 스키마 검증 (constraints/indexes missing 감지)
- `chainsight/graph/repository.py:139-144` — health_check() (connectivity 확인)

**미구현 (HIGH)**:
- PG에 있고 Neo4j에 없는 노드/엣지 감지 — **없음**
- Neo4j에 있고 PG에 없는 노드/엣지 감지 — **없음**
- 양방향 reconciliation 태스크 — **없음**
- PG ↔ Neo4j 속성 값 불일치 감지 — **없음**
- `verify_schema()` 자동 호출 — **없음** (수동 실행만 가능)

### 3.5 Neo4j 대응 모델 맵

| Django 모델 | Neo4j 노드/엣지 | Dirty 플래그 | 동기화 태스크 | 위험 |
|-------------|-----------------|-------------|-------------|------|
| SupplyChainEvidence | Stock↔Stock 엣지 (sec_10k) | neo4j_dirty | sync_dirty_to_neo4j | Stock 삭제 시 PG CASCADE → Neo4j 미정리 |
| RelationConfidence | Stock↔Stock 타입별 엣지 | neo4j_dirty | run_neo4j_dirty_sync | save() 자동 dirty, 양호 |
| CompanyChainProfile | Stock 노드 속성 | neo4j_synced | sync_profiles_to_neo4j | Stock 삭제 시 Neo4j 고아 노드 |
| NewsArticle | NewsEvent 노드 + Impact 엣지 | **없음** | sync_news_to_neo4j | 30일 TTL 의존, 정리 태스크 미확인 |
| CoMentionEdge | CO_MENTIONED 엣지 | **없음** | **없음** | PG-only 모델이나 Neo4j에도 해당 엣지 존재 |
| PriceCoMovement | PRICE_CORRELATED 엣지 | **없음** | **없음** | 동기화 메커니즘 불명확 |

**핵심 Gap**: Stock이 PG에서 CASCADE 삭제되면 Neo4j의 해당 노드/엣지는 그대로 남음. `post_delete` 시그널이 `rag_analysis/signals.py`에만 존재하며 chainsight, sec_pipeline에는 없음.

---

## 4. Unique 제약조건 현황

### 4.1 unique_together / UniqueConstraint 설정 (35+ 모델)

| 앱 | 모델 | 제약 필드 | 위치 |
|----|------|----------|------|
| stocks | DailyPrice | (stock, date) | models.py:185 |
| stocks | WeeklyPrice | (stock, date) | models.py:214 |
| users | Portfolio | (user, stock) | models.py:71 |
| users | Watchlist | (user, name) | models.py:179 |
| users | WatchlistItem | (watchlist, stock) | models.py:217 |
| users | UserInterest | (user, interest_type, value) | models.py:265 |
| serverless | MarketMover | [date, mover_type, symbol] | models.py:105 |
| serverless | VolatilityBaseline | [symbol, date] | models.py:161 |
| serverless | StockKeyword | [symbol, date] | models.py:245 |
| serverless | SectorPerformance | [date, sector] | models.py:562 |
| serverless | CorporateAction | [symbol, date, action_type] | models.py:614 |
| serverless | StockRelationship | [source_symbol, target_symbol, relationship_type] | models.py:946 |
| serverless | CategoryCache | [symbol, date] | models.py:981 |
| serverless | ETFHolding | [etf, stock_symbol, snapshot_date] | models.py:1100 |
| serverless | ThemeMatch | [stock_symbol, theme_id] | models.py:1172 |
| serverless | LLMExtractedRelation | 복합 필드 | models.py:1311 |
| serverless | InstitutionalHolding | [institution_cik, stock_symbol, report_date] | models.py:1389 |
| validation | CompanyMetricLatest | [symbol, metric_code] | metric_latest.py:47 |
| validation | PeerPreset | [symbol, preset_key] | peer_preset.py:36 |
| validation | UserPeerPreference | [user, symbol] | peer_preset.py:63 |
| validation | CompanyBenchmarkDelta | [symbol, fiscal_year, metric_code, preset_key] | benchmark_delta.py:60 |
| validation | CategorySignal | [symbol, category, fiscal_year, preset_key] | category_score.py:58 |
| metrics | CompanyMetricSnapshot | [symbol, fiscal_year, metric_code] | metric_snapshot.py:69 |
| metrics | IndustryMetricBenchmark | [industry, fiscal_year, metric_code] | benchmark.py:87 |
| metrics | PeerMetricBenchmark | [symbol, fiscal_year, metric_code, preset_key] | benchmark.py:138 |
| macro | IndicatorValue | [indicator, date] | indicators.py:133 |
| macro | MarketIndexPrice | [index, date] | indicators.py:229 |
| macro | SectorIndicatorRelation | [indicator, sector_code, condition_type] | relationships.py:94 |
| macro | IndicatorCorrelation | [indicator_a, indicator_b] | relationships.py:165 |
| news | NewsEntity | [news, symbol] | models.py:292 |
| news | SentimentHistory | [symbol, date] | models.py:380 |
| graph_analysis | CorrelationMatrix | [watchlist, date] | models.py:51 |
| graph_analysis | CorrelationEdge | [watchlist, stock_a, stock_b, date] | models.py:127 |
| chainsight | ChainNewsEvent | [source, source_id] | news_event.py:63 |
| sec_pipeline | RawDocumentStore | accession_no (unique field) | models.py:28 |
| sec_pipeline | CompanyAlias | (alias, context_sector) | models.py:295 |

### 4.2 Unique 제약조건 누락 의심 모델

| 모델 | 추정 필요 제약 | 위험도 | 근거 |
|------|--------------|--------|------|
| `MarketBreadth` (serverless) | [date, indicator_type] | HIGH | 날짜+지표 조합이 논리적 유일키이나 미설정 |
| `EODSignal` (stocks) | [stock, date] | LOW | bulk_create(update_conflicts=True)로 코드 레벨 보호 |
| `IndicatorReading` (thesis) | [indicator, date] or 유사 | MEDIUM | update_or_create 사용하나 unique 미확인 |
| OneToOne 모델들 (chainsight) | symbol (PK) | LOW | OneToOneField(primary_key=True)로 암묵적 보호 |

### 4.3 update_or_create Race Condition 분석

**전체**: 75+ 곳에서 `update_or_create` 사용

| 분류 | 건수 | 비율 | 위험도 |
|------|------|------|--------|
| `transaction.atomic()` + `IntegrityError` 처리 | ~12 | 16% | LOW |
| `transaction.atomic()`만 적용 | ~11 | 15% | MEDIUM |
| 보호 없음 (bare call) | ~52 | 69% | **HIGH** |

**안전한 사용처** (atomic + IntegrityError):
- `api_request/alphavantage_service.py` — DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement
- `api_request/stock_service.py` — DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement
- `serverless/services/patent_network_service.py` — StockRelationship

**위험한 사용처** (보호 없음, 대표 사례):
- `validation/services/metric_calculator.py:99` — CompanyMetricSnapshot
- `validation/services/preset_generator.py:118,147,178,286,362,449` — PeerPreset (6곳)
- `validation/services/benchmark_calculator.py:239,273,331` — PeerMetricBenchmark, CompanyBenchmarkDelta, IndustryMetricBenchmark
- `chainsight/tasks/relation_tasks.py:275,309,344` — RelationConfidence
- `chainsight/tasks/profile_tasks.py:107,181` — CompanyGrowthStage, CompanyCapitalDNA
- `serverless/services/keyword_service.py:202` — StockKeyword
- `serverless/services/corporate_action_service.py:222` — CorporateAction
- `serverless/services/theme_matching_service.py:247,329,575` — ThemeMatch
- `thesis/tasks/eod_pipeline.py:239,256,268` — IndicatorReading

**Race Condition 시나리오**: Celery 워커 2개가 동일 symbol+date의 DailyPrice를 동시에 `update_or_create` → 둘 다 SELECT에서 미존재 확인 → 둘 다 INSERT 시도 → `IntegrityError`. atomic 미적용 시 unhandled exception으로 태스크 실패.

### 4.4 bulk_create 사용 현황

| 위치 | 모델 | update_conflicts | atomic | 위험 |
|------|------|-----------------|--------|------|
| stocks/services/eod_pipeline.py:347 | EODSignal | True (unique_fields 지정) | Yes | LOW |
| serverless/services/etf_csv_downloader.py:981 | ETFHolding | 미지정 | No | MEDIUM |
| sec_pipeline/validator_track_a.py:163 | SupplyChainEvidence | 미지정 | No | MEDIUM |
| sec_pipeline/validator_track_b.py:110 | BusinessModelEvidence | 미지정 | No | MEDIUM |
| thesis/services/keyword_cache.py:41 | KeywordCache | 미지정 | No | LOW |
| graph_analysis/services/correlation_calculator.py:372 | CorrelationEdge | 미지정 | Yes | LOW |

---

## 부록: 권장사항 요약

### CRITICAL 우선순위

1. **Stock/User soft delete 구현**: `is_deleted` + `deleted_at` 필드 추가, CASCADE 대신 PROTECT 전환 검토
2. **update_or_create 일괄 atomic 적용**: 최소 52곳의 bare call에 `transaction.atomic()` 래핑
3. **Stock 삭제 시 Neo4j 정리 시그널**: `post_delete(Stock)` 시그널에서 관련 Neo4j 노드/엣지 삭제 추가

### HIGH 우선순위

4. **Neo4j reconciliation 태스크**: PG ↔ Neo4j 주기적 양방향 정합성 검사 Celery Beat 등록
5. **Orphan 정리 management command**: `AnalysisSession(basket=NULL)`, `UsageLog(session=NULL)` 등 주기 정리
6. **MarketBreadth unique 제약**: `[date, indicator_type]` unique_together 추가
7. **News Neo4j TTL 정리 태스크**: 만료된 NewsEvent 노드 자동 삭제 Celery Beat 등록

### MEDIUM 우선순위

8. **neo4j_dirty 패턴 통일**: `neo4j_synced` → `neo4j_dirty` 마이그레이션 (chainsight/CompanyChainProfile)
9. **IntegrityError 처리 추가**: update_or_create 호출부에 try/except IntegrityError
10. **verify_schema() 자동화**: Celery Beat에서 주기적 Neo4j 스키마 검증 + 알림

---

*이 보고서는 코드 읽기 전용으로 수행되었으며, 어떤 코드도 수정하지 않았습니다.*
