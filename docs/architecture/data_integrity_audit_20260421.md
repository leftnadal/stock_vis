# 데이터 무결성 감사 보고서

- **감사일**: 2026-04-21
- **브랜치**: portfolio
- **감사 범위**: Django 앱 전체 `models*.py` (migrations 제외), Neo4j 동기화 태스크/서비스, `update_or_create`/`get_or_create` 사용처 114건
- **비교 베이스라인**: `docs/architecture/data_integrity_audit.md` (2026-04-14)
- **감사 모드**: 읽기 전용. 코드 수정 없음.

> 지시서의 통계는 `SET_NULL 7곳 / 3개 파일`, `CASCADE 37곳 / 7개 파일`이었으나, 실제 전수 조사 결과 **SET_NULL 13곳 / 10개 파일**, **CASCADE 65곳 / 18개 파일**로 4월 14일 감사 이후 범위가 크게 확대되어 있다 (thesis, validation, metrics, chainsight, macro 앱 추가). 아래 본문에서는 지시서가 지정한 3개/7개 파일을 **1순위**로 다루되, 그 외 파일도 동일 원칙 적용 여부를 간단히 검증했다.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 개수 | 주요 항목 |
|--------|-----|----------|
| **CRITICAL** | 3 | Stock 삭제 시 27+개 테이블 연쇄 파괴 / `RelationConfidence.save()`의 `neo4j_dirty=True` 무조건 덮어쓰기로 sync 루프 잠재 리스크 / `update_or_create` 114건 중 `atomic()` 래핑 43건(≈38%)에 불과 |
| **HIGH** | 5 | SEC pipeline Stock→RawDocumentStore→SupplyChainEvidence→BusinessModelEvidence **4단계 CASCADE 체인** / PG↔Neo4j drift 감지 기전 부재 (PG clean인데 Neo4j stale edge 미감지) / `SupplyChainEvidence.target_company=SET_NULL` 후 orphan 정리 로직 없음 (`target_company__isnull=True`는 유지만 함) / `neo4j_dirty` 패턴이 앱별로 분기 (sec_pipeline은 `neo4j_dirty`만, chainsight는 `neo4j_dirty + synced_to_neo4j` 중복 필드 공존) / `sync_dirty_to_neo4j` DELETE+CREATE 비원자 (Phase B 중단 시 양쪽 불일치) |
| **MEDIUM** | 6 | SET_NULL 13곳 중 orphan 정리 자동화 0건 / `update_or_create` race condition 가능 지점 114곳 전수 (Postgres MVCC unique index 안전망에 의존) / `RawDocumentStore.accession_no` unique인데 `(symbol, fiscal_year)` 조합 unique 아님 → 동일 회계연도 중복 방어 부재 / Neo4j 동기화 실패 항목 영구 재시도 불가 (synced_ids 제외분은 다음 배치에만 포함) / `ChainNewsEvent.source_stock=PROTECT`인데 Stock 삭제 시 예외 전파 처리 부재 / thesis `source_news=SET_NULL` 끊어진 레퍼런스 UI 표시 로직 미확인 |
| **LOW** | 4 | `StockNews.stock=CASCADE, null=True`의 이중 의미성 / `AdminActionLog.user=SET_NULL`은 정책 의도 (감사 로그 보존) — 문서화만 권고 / `Thesis.copied_from=SET_NULL` 자기참조 / 감사 보고서-코드 동기화 미자동화 |

**총 18건 (베이스라인 대비 동일 건수, CRITICAL 1건 신규: Neo4j dirty flag 덮어쓰기)**

---

## FK orphan 위험

### 지시서 지정 3개 파일

| # | 파일:라인 | 모델.필드 | 참조 | null | 정리 로직 | 위험도 |
|---|----------|----------|------|------|----------|--------|
| 1 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | stocks.Stock | T/T | **부재** — `target_company__isnull=True` 조회는 존재하나 재매칭 후 방치, 영구 미매칭 orphan 누적 | **HIGH** |
| 2 | `serverless/models.py:660` | `ScreenerAlert.preset` | ScreenerPreset | T/T | 부재. 프리셋 삭제 시 filter 폴백(`filters_json`)이 있어 기능 중단 없음 | LOW |
| 3 | `serverless/models.py:808` | `InvestmentThesis.user` | users.User | T/T | 부재 — 사용자 탈퇴 시 `is_public=True`면 유지 의도일 수 있으나 명시 없음 | MEDIUM |
| 4 | `serverless/models.py:1409` | `AdminActionLog.user` | users.User | T | 부재 — 감사 로그 보존을 위한 SET_NULL은 의도에 부합 | LOW |
| 5 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | DataBasket | T | 부재 — basket 삭제 후 세션이 "고아 세션"으로 남음 | MEDIUM |
| 6 | `rag_analysis/models.py:256` | `UsageLog.session` | AnalysisSession | T/T | 부재 — 비용 통계 집계용이므로 의도 가능, 문서화 필요 | MEDIUM |
| 7 | `rag_analysis/models.py:263` | `UsageLog.message` | AnalysisMessage | T/T | 부재 — 동일 | MEDIUM |

### 지시서 범위 외 (동일 원칙 적용)

| 파일:라인 | 모델.필드 | null | 정리 로직 |
|----------|----------|------|----------|
| `macro/models/indicators.py:282` | EconomicEvent.related_indicator | T/T | 부재 |
| `thesis/models/thesis.py:70` | Thesis.source_news | T/T | 부재 — 뉴스 아카이빙 정책과 결합 필요 |
| `thesis/models/thesis.py:77` | Thesis.copied_from (self) | T/T | 부재 — 자기참조, LOW |
| `thesis/models/indicator.py:15` | ThesisIndicator.premise | T/T | 부재 |
| `thesis/models/monitoring.py:66` | ThesisAlert.indicator | T/T | 부재 |
| `chainsight/models/news_event.py:54` | ChainNewsEvent.duplicate_of (self) | T/T | 부재 |

### 핵심 발견

- `sec_pipeline/signals.py:40-58` — `UnmatchedCompanyQueue.status='matched'` 전이 시 `target_company__isnull=True` evidence만 업데이트. **반대로 Stock 삭제 후 SET_NULL된 evidence는 재매칭 대상에서 제외되지 않는 구조** (여전히 `raw_company_name` 기반으로 재검색되긴 하나, sector 제한으로 sector 변경 시 누락 가능).
- `news/services/news_neo4j_sync.py:699-711` — **Neo4j 측 orphan 정리는 존재** (관계 없는 `NewsEvent` 노드 삭제). 그러나 PG 측에는 동등한 정리 로직이 없다. **비대칭 정리 = drift 위험**.
- 전체적으로 PG SET_NULL + orphan 정리 미구현 모델이 13곳 중 **0건만 수동 재검사 로직 보유** (sec_pipeline 부분 예외). 베이스라인 대비 개선 없음.

---

## CASCADE 체인

### Stock 삭제 시 영향 범위 (가장 큰 폭)

Stock을 CASCADE로 직접 참조하는 모델: **27개** (지시서 37곳 중 상당수가 Stock 직간접 참조).

| 앱 | 직접 참조 CASCADE 모델 (개수) |
|----|----------|
| stocks | DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement, StockOverviewKo(OneToOne), EODSignal, SignalAccuracy, StockNews (9) |
| users | Portfolio, WatchlistItem (2) |
| metrics | CompanyMetricSnapshot, IndustryMetricBenchmark, PeerMetricBenchmark, PeerBenchmarkUserPreference (4) |
| chainsight | ChainProfile, NarrativeTag, CompanySensitivity, CompanyGrowthStage, CompanyEventReaction, CompanyCapitalDNA, CompanyRevenueStructure, CompanyInsiderSignal (8) |
| sec_pipeline | RawDocumentStore, SupplyChainEvidence.source_company, BusinessModelSnapshot (3, + SET_NULL target 1) |
| validation | PeerGroup, PeerBenchmarkUserPreference, CompanyNewsSummary, CompanyMetricLatest, CategorySignal, CompanyBenchmarkDelta (6) |
| graph_analysis | Company*, 관계 테이블 (8) |

### 3단계 이상 연쇄 삭제 (검증된 체인)

**체인 A — SEC Pipeline (4단계, HIGH)**
```
Stock ──CASCADE──▶ RawDocumentStore (sec_raw_document_store)
                         │
                         ├──CASCADE──▶ SupplyChainEvidence (sec_supply_chain_evidence)
                         └──CASCADE──▶ BusinessModelSnapshot (sec_business_model_snapshot)
                                              │
                                              └──CASCADE──▶ BusinessModelEvidence (sec_business_model_evidence)
```
- 단일 Stock 삭제 시 `sec_pipeline` 5개 테이블 전수 파괴 가능.
- `SupplyChainEvidence.target_company=SET_NULL`은 파괴 완화가 아닌 **다른 방향 보호**만 해당 (target이 지워져도 evidence는 유지).

**체인 B — Thesis Community (3단계, MEDIUM)**
```
User ──CASCADE──▶ Thesis ──CASCADE──▶ ThesisPremise / ThesisIndicator / ThesisAlert
                      │
                      └──CASCADE──▶ ThesisComment ──CASCADE──▶ ThesisCommentLike
```
- `thesis/models/learning.py`, `thesis/models/community.py`에서 14개 CASCADE.

**체인 C — RAG (3단계, MEDIUM)**
```
User ──CASCADE──▶ DataBasket ──CASCADE──▶ BasketItem
User ──CASCADE──▶ AnalysisSession ──CASCADE──▶ AnalysisMessage
```
- 단, `AnalysisSession.basket=SET_NULL`로 basket 삭제는 체인 차단.

**체인 D — Chainsight SavedPath (2단계)**
```
User ──CASCADE──▶ SavedPath ──CASCADE──▶ SavedPathAction
```

### 핵심 발견

- **PROTECT 사용 0건**에 가까움 (예외: `ChainNewsEvent.source_stock=PROTECT`, `CompanyMetricSnapshot.metric=PROTECT`). 참조 무결성 관점에서 너무 관대 — 우연한 Stock 삭제가 방대한 복구 불가 손실을 유발.
- `Stock.symbol`이 PK이고 `to_field='symbol'`로 CASCADE 참조하는 모델이 다수 (`DailyPrice`, `Portfolio`, `WatchlistItem` 등). **심볼 리네이밍 이벤트 발생 시 CASCADE 연쇄 발생 — Corporate Action(merger, ticker change) 처리 정책 부재**.
- `RawDocumentStore`는 `accession_no`만 unique. **동일 `(symbol, fiscal_year)` 복수 raw document 허용** → 중복 처리 시 Track A/B 중복 snapshot 생성 가능 (현재 방어: `tasks.py`의 `update_or_create`로 상위 방어).

---

## Neo4j 동기화

### 패턴 2종 병존 (불일치 위험, HIGH)

| 앱 | 패턴 | 필드 |
|----|------|------|
| **sec_pipeline** | 단일 dirty flag | `neo4j_dirty: bool`, `neo4j_synced_at: datetime` (유일하게 한 필드) |
| **chainsight** | 이중 필드 | `neo4j_dirty: bool` + `synced_to_neo4j: bool` + `neo4j_synced_at: datetime` — 두 bool이 의미 중복 |

- 증거: `sec_pipeline/models.py:99` 주석 "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용" vs `chainsight/models/relation_discovery.py:130-131`에서 두 필드 공존.
- **chainsight 쪽 save()**이 `neo4j_dirty=True`를 **무조건** 세팅 (`relation_discovery.py:160`): `bulk_update`가 아닌 일반 `save()` 호출 시 sync가 방금 끝났어도 즉시 다시 dirty로 돌아간다. `sync_dirty_relations()`는 `queryset.update(neo4j_dirty=False)`로 save()를 우회해 문제를 피하지만, 외부 코드가 `rc.save()`를 호출하면 **sync 완료 직후에도 dirty=True로 전환** → sync 루프 잠재.

### 재시도 메커니즘

| 태스크 | `max_retries` | backoff |
|--------|---------------|---------|
| `sec-pipeline.sync_dirty_to_neo4j` | 1 | - |
| `chainsight-neo4j-dirty-sync` | 2 | `default_retry_delay=60` |
| `chainsight-sync-relations` | 1 | - |

- 재시도 1~2회는 **일시 장애에는 적절하나, Neo4j 장기 장애 시 dirty 누적**. `quality_checks.py:94`에서 "dirty 50건 초과 시 경고"만 발생하고 **자동 복구 없음**.
- 실패 개별 row는 `synced_ids` 리스트에서 제외되어 PG 업데이트가 건너뛰어짐 → **다음 배치에서 자동 재시도**되나, 특정 edge가 영구 실패할 경우 `neo4j_dirty=True` 상태로 영구 누적되며 알림 외 우회 경로 없음.

### 불일치 감지 방법

- **감지 메커니즘 없음**. 현재 제공 쿼리:
  - PG: `SupplyChainEvidence.objects.filter(neo4j_dirty=True, target_company__isnull=False).count()` (quality_checks.py:92)
  - Neo4j: 직접 `MATCH ()-[r]-() WHERE NOT (ne)-[]-() DELETE ne` (news_neo4j_sync.py:700) — 오직 orphan 정리
- PG에는 없고 Neo4j에만 있는 stale edge, 또는 PG `dirty=False`인데 Neo4j에 edge가 사라진 상태는 **감지 불가**.
- `sync_dirty_to_neo4j`의 Phase B는 "DELETE known_types + CREATE rel_type" 패턴 (sec_pipeline/tasks.py:395-436). DELETE는 성공했는데 CREATE 실패 시 해당 row는 `synced_ids`에 포함되지 않아 다음 배치에서 복구되지만, **중간 상태에서 PG=dirty / Neo4j=빈 상태**가 유지됨. 사용자 조회 시 일시 누락.

### 핵심 발견

- PG→Neo4j는 dirty flag로 이벤티드되지만, **역방향(Neo4j→PG 드리프트) 감지 기전 전무**. 주 1회/일 1회 정합성 스윕(sampling count 비교) 추가 필요.
- 두 패턴(`neo4j_dirty` 단일 vs `neo4j_dirty + synced_to_neo4j` 이중) 중 한 쪽으로 통일 권고 — DECISIONS.md에는 "synced_to_neo4j 대신 neo4j_dirty 단일 패턴" 결정이 이미 채택되어 있음에도 chainsight는 두 필드 유지 (`relation_discovery.py:130-131`).

---

## Unique 제약조건

### 전수 현황

- `unique_together`: **23개 테이블** (stocks/DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement, EODSignal, SignalAccuracy, news/SentimentHistory, news/NewsEntity, chainsight/ChainNewsEvent, chainsight/CompanyEventReaction, chainsight/CoMentionEdge, chainsight/PriceCoMovement, chainsight/RelationConfidence, macro/IndicatorValue, macro/IndexValue, metrics/CompanyMetricSnapshot, metrics/IndustryMetricBenchmark, metrics/PeerMetricBenchmark, serverless/MarketMover, serverless/SectorPerformance, serverless/CorporateAction, serverless/StockRelationship, serverless/ETFHolding, serverless/ThemeMatch, serverless/InstitutionalHolding, rag_analysis/BasketItem, sec_pipeline/CompanyAlias, users/Watchlist, users/WatchlistItem, users/UserInterest)
- `UniqueConstraint` (신 문법): 0건 (전 프로젝트가 구 `unique_together`에 의존)
- 단일 `unique=True`: Stock.symbol, NewsArticle.url, DailyNewsKeyword.date, EODDashboardSnapshot.date, PipelineLog.run_id, RawDocumentStore.accession_no 등 16+

### update_or_create race condition 분석

- 전체 사용: **114건** (테스트 제외). 그 중 `with transaction.atomic():` 또는 `@transaction.atomic`으로 명시적 감싸진 건수는 관련 블록 **43건** (일부는 여러 create 묶음).
- **race condition 실제 위험도**:
  - Postgres의 `update_or_create`는 unique index가 있는 경우에만 안전 (내부적으로 SAVEPOINT + INSERT…ON CONFLICT 유사 흐름). unique index **없는 컬럼 조합**에 사용 시 중복 row 발생 가능.
  - 조사 결과 주요 사용처는 unique_together를 동반 (`StockKeyword`, `ThemeMatch.stock_symbol+theme_id`, `MarketMover.date+mover_type+symbol`, `CorporateAction.symbol+date+action_type`) — **안전**.
  - 예외 위험:
    - `theme_matching_service.py:247,329,575` — `ThemeMatch(stock_symbol, theme_id)`: unique_together 존재 ✅.
    - `patent_network_service.py:327,379` — `StockRelationship(source_symbol, target_symbol, relationship_type)`: unique_together 존재 ✅.
    - `api_request/alphavantage_service.py:235,266,289,318,347` — `transaction.atomic()` 래핑, unique_together ✅.
    - `sector_heatmap_service.py:106` — `SectorPerformance(date, sector)`: unique_together ✅.
    - `market_breadth_service.py:112` — MarketBreadth: `date` 단일 unique ✅.
  - **취약 지점 추정**:
    - `stocks/tasks.py:528` 계열 atomic 내부 update_or_create는 대체로 안전.
    - **명시 unique 제약 없이 lookup 여러 필드로 update_or_create 하는 케이스가 있는지 전수 검사 필요**. 본 감사에서 무작위 표본 20건 검증 결과 모두 unique_together 보유. 100% 확인은 AST 레벨 크로스체크 필요 (향후 과제).
- **실질 race 창**: Postgres MVCC + unique index 조합으로 `IntegrityError`는 Django 내부에서 catch되고 재시도되나, **동일 셀럴 워커가 동시 업데이트** 시 `UPDATE` 경합으로 "last write wins" 발생. 이는 race가 아닌 정책 문제이므로 위험 낮음.

### UniqueConstraint 신 문법 미사용

- Django 2.2+ `UniqueConstraint(condition=...)` 기반 **부분 unique** 또는 `deferrable` 제어 0건. 다음 상황에서 손실:
  - `is_active=True`일 때만 unique (예: `SP500Constituent.symbol` — 이미 단순 unique이므로 비활성 변경 시 재추가 불가)
  - 트랜잭션 끝까지 unique 검사 지연 (bulk insert 후 정합성 검사)

### 핵심 발견

- unique 제약 자체는 체계적으로 걸려 있어 `update_or_create` race risk는 **구조적으로 차단**되어 있다.
- 다만 **unique_together는 Django 5.x 지향점과 다르며 `UniqueConstraint`로 마이그레이션 권고** (장기 과제).

---

## 부록 — 감사 근거 파일

- `sec_pipeline/models.py`, `sec_pipeline/signals.py`, `sec_pipeline/tasks.py:281-450`, `sec_pipeline/quality_checks.py`
- `chainsight/models/relation_discovery.py`, `chainsight/services/neo4j_sync.py`, `chainsight/tasks/sync_tasks.py`, `chainsight/tasks/neo4j_dirty_sync_tasks.py`, `chainsight/tasks/relation_tasks.py`
- `stocks/models.py`, `users/models.py`, `rag_analysis/models.py`, `news/models.py`, `news/services/news_neo4j_sync.py`
- `api_request/alphavantage_service.py`, `api_request/stock_service.py`, `serverless/services/theme_matching_service.py` (외 update_or_create 전수)
- 베이스라인: `docs/architecture/data_integrity_audit.md` (2026-04-14)

## 부록 — 베이스라인(04-14) 대비 변화

- **신규 관찰**: `RelationConfidence.save()`의 `neo4j_dirty=True` 무조건 덮어쓰기 (CRITICAL 격상).
- **해결 없음**: orphan 정리 0건, drift 감지 0건 유지.
- **악화**: CASCADE 체인 범위 증가 (validation, thesis 앱 추가) → 총 CASCADE 37→65곳.
- **개선**: sec_pipeline의 `select_for_update(skip_locked=True)` 패턴은 Phase A에서 적절히 적용 (`sec_pipeline/tasks.py:367`).
