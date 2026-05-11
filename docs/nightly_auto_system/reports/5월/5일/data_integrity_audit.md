# 데이터 무결성 감사 보고서

- 감사 일자: 2026-05-05
- 감사 범위: PostgreSQL FK 정책, Neo4j 동기화 메커니즘, 동시성 제약
- 모드: 읽기 전용 (코드 수정 없음)
- 대상 모델 파일: 13개 앱 × 27개 models 파일

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|---|---|---|
| 🔴 High | 4 | Stock 삭제 시 PROTECT/CASCADE 충돌, neo4j_dirty 이중 플래그(`synced_to_neo4j`+`neo4j_dirty`), Neo4j → PG 역방향 불일치 감지 없음, SET_NULL 후 orphan 누적 정리 미구현 |
| 🟡 Medium | 5 | `update_or_create` race condition (Celery 동시 실행), `bulk_update` 시 `neo4j_dirty` 자동 갱신 누락, 4단계 CASCADE 체인(`Stock → AnalysisRun → MetricResult/LLMComment` PROTECT 충돌), `target_company` SET_NULL 후 재매칭 큐 적체, `to_field='symbol'` CASCADE — Stock symbol 변경 시 자식 갱신 누락 |
| 🟢 Low | 3 | `synced_to_neo4j` 레거시 필드 잔존, RAG `AnalysisSession` SET_NULL → `UsageLog` orphan, ScreenerAlert `preset` SET_NULL 후 `filters_json` fallback (정상 패턴) |

**핵심 결론**:
- 사용자 사전 파악 수치 (SET_NULL 7곳/3파일, CASCADE 37곳/7파일)은 **과소집계**. 실제 SET_NULL은 **16곳/9파일**, CASCADE는 **80+ 곳/15파일** (`thesis/`, `metrics/`, `validation/`, `chainsight/`, `portfolio/`, `macro/` 추가 파일에 분산).
- Stock 삭제는 사실상 **불가능** — `portfolio/MetricResult`, `metrics/CompanyMetricSnapshot`, `chainsight/ChainNewsEvent`가 **PROTECT** 걸어둔 상태에서 동시에 `users/Portfolio`, `chainsight/CapitalDNA` 등은 CASCADE → 동일 Stock 삭제 트랜잭션이 PROTECT에서 막혀 전체 롤백.
- Neo4j 동기화는 **단방향** (PG → Neo4j). 역방향 감지 로직은 `news/services/news_neo4j_sync.py`의 NewsEvent 고아 노드 정리만 존재.

---

## FK orphan 위험

### 1. SET_NULL 사용처 — 실제 16곳 (사용자 사전 파악 7곳 대비 +9)

| 파일 | 줄 | 모델/필드 | 부모 삭제 시 영향 | orphan 정리 로직 |
|---|---|---|---|---|
| `sec_pipeline/models.py` | 86 | `SupplyChainEvidence.target_company` → Stock | Stock 삭제 시 evidence는 남고 target_company=NULL | ❌ 없음. `signals.py`는 매칭만, 미매칭 evidence는 누적 |
| `serverless/models.py` | 660 | `ScreenerAlert.preset` → ScreenerPreset | preset 삭제 시 alert는 살아남고 `filters_json` fallback | ✅ `get_effective_filters()`로 graceful degradation |
| `serverless/models.py` | 808 | `InvestmentThesis.user` → User | 사용자 탈퇴 시 thesis 익명화 | ❌ 익명 thesis 누적 정리 없음 |
| `serverless/models.py` | 1409 | `AdminActionLog.user` → User | admin 탈퇴 시 감사 로그 익명화 | ✅ 의도적 (감사 추적 보존) |
| `rag_analysis/models.py` | 145 | `AnalysisSession.basket` → DataBasket | basket 삭제 시 세션 컨텍스트 손실 | ❌ 없음 |
| `rag_analysis/models.py` | 256, 263 | `UsageLog.session/message` → AnalysisSession/Message | 세션 삭제 후 비용 로그만 남음 | ❌ session_id NULL인 UsageLog 누적 가능 |
| `thesis/models/thesis.py` | 70, 77 | `Thesis.source_news`, `Thesis.copied_from` | NewsArticle/원본 thesis 삭제 시 출처 끊김 | ❌ 출처 단절 감지 없음 |
| `thesis/models/indicator.py` | 15 | `ThesisIndicator.indicator_metric` → metrics.MetricDefinition | 지표 정의 삭제 시 thesis 추적 단절 | ❌ |
| `thesis/models/monitoring.py` | 66 | (관제 스냅샷의 thesis FK) | 스냅샷-원본 thesis 단절 | ❌ |
| `macro/models/indicators.py` | 282 | `EconomicEvent.related_indicator` | 지표 삭제 시 이벤트 분리 | ❌ |
| `portfolio/models.py` | 327 | `AnalysisRun.wallet_snapshot_at_execution` | 스냅샷 삭제 시 run 메타 분리 | ⚠️ `is_finalized=True` 시 보호되나 스냅샷은 별도 |
| `portfolio/models.py` | 732 | `ChatSession.analysis_run` | run 삭제 시 채팅 보존 | ❌ |
| `portfolio/models.py` | 831 | `Decision.context_analysis_run` | run 삭제 시 의사결정 컨텍스트 분리 | ❌ |
| `chainsight/models/news_event.py` | 54 | `ChainNewsEvent.duplicate_of` (self FK) | 중복 원본 삭제 시 dedup 체인 끊김 | ❌ |

### 2. 권장 보강 항목

- **누적 NULL 모니터링**: `target_company__isnull=True` 카운트는 `sec_pipeline/intelligence.py`에서만 추적. 다른 SET_NULL 필드(특히 `UsageLog.session=NULL`, `Thesis.source_news=NULL`, `EconomicEvent.related_indicator=NULL`)는 무한 누적되며 어드민/대시보드에 노출 안 됨.
- **개인정보 관점**: `InvestmentThesis.user=NULL` (탈퇴 익명화)은 GDPR/개인정보 요구사항에 부합하지만, 동시에 thesis 자체에 user 식별자가 `filters_snapshot` JSON에 박혀 있을 가능성 검증 필요 (해당 보고서에서 미확인).

---

## CASCADE 체인

### 1. Stock 삭제 영향 범위 — 가장 큰 fan-out (직접 자식 30+ 모델)

`stocks.Stock`을 직접 참조하는 ForeignKey 분포:

| 정책 | 모델 (앱) | 비고 |
|---|---|---|
| **CASCADE** | `DailyPrice`, `WeeklyPrice`, `StockOverviewKO`, `IncomeStatement`, `BalanceSheet`, `StockNews` (stocks) | `to_field='symbol'` 사용 — symbol 변경 시 자식 자동 갱신 |
| **CASCADE** | `Portfolio`, `WatchlistItem` (users) | 사용자 데이터 동시 삭제 |
| **CASCADE** | `CompanyChainProfile`, `CompanyCapitalDNA`, `CompanyGrowthStage`, `CompanyInsiderSignal`, `CompanyNarrativeTag`, `CompanyRevenueStructure`, `CompanySensitivity`, `CompanyEventReaction` (chainsight) | OneToOne 6개 + FK 2개 |
| **CASCADE** | `CompanyMetricLatest`, `CompanyBenchmarkDelta`, `CategoryScore`, `ValidationNewsSummary`, `PeerPreset` × 2 (validation) | preset 5개 모두 |
| **CASCADE** | `IndustryMetricBenchmark`, `PeerMetricBenchmark` (metrics) | |
| **CASCADE** | `SupplyChainEvidence.source_company` (sec_pipeline) + `RawDocumentStore.symbol` + `BusinessModelSnapshot.symbol` | source 측 |
| **SET_NULL** | `SupplyChainEvidence.target_company` (sec_pipeline) | target 측만 SET_NULL |
| **🔴 PROTECT** | `WalletHolding`, `MetricResult`, `DiagnosticCard.target_stock`, `LLMComment` (portfolio) | 4곳 |
| **🔴 PROTECT** | `CompanyMetricSnapshot.symbol` (metrics) | 1곳 |
| **🔴 PROTECT** | `ChainNewsEvent.symbol` (chainsight) | 1곳 |

### 2. Stock 삭제 시 실제 동작 (🔴 High 위험)

```
Stock.delete()
  ├── CASCADE 30+ 모델 삭제 시도 (Phase 1)
  ├── 동일 트랜잭션 내 PROTECT 6모델 → IntegrityError
  └── 전체 롤백 → Stock도 살아남음
```

**결론**: Stock 삭제는 PROTECT 때문에 **항상 실패**. 그러나 명시적 운영 절차/문서/마이그레이션 정책이 없어, 운영자가 강제 삭제를 시도할 경우 어느 PROTECT가 막을지 예측 불가. 또한 `to_field='symbol'`을 쓰는 6개 모델은 PK가 아닌 symbol 컬럼을 참조하므로, **Stock symbol 변경 시 자식 모두 ON UPDATE CASCADE로 갱신**되는데(Postgres 기본 정책 의존), Django 마이그레이션은 ON UPDATE를 명시하지 않음 — symbol rename 시 자식 데이터 정합성 검증 필요.

### 3. 3단계 이상 연쇄 삭제 체인

#### 체인 A: User → Portfolio → AnalysisRun → MetricResult/LLMComment (4단계)
```
User (CASCADE) → Portfolio
  └─ Portfolio (CASCADE) → AnalysisRun
       ├─ AnalysisRun (CASCADE) → MetricResult.analysis_run
       │    └─ MetricResult.stock = PROTECT  ⚠️ 사용자 탈퇴 시 PROTECT 충돌 가능
       └─ AnalysisRun (CASCADE) → LLMComment.analysis_run
            └─ LLMComment.stock = PROTECT  ⚠️ 동일
```
🟡 Medium 위험: **User 탈퇴 시** AnalysisRun이 CASCADE로 사라지고, MetricResult/LLMComment의 `analysis_run` FK는 CASCADE로 전파되므로 **이 경로는 안전**. 단, `stock`이 PROTECT인 것은 Stock 삭제 시점만 막음 — User 삭제 흐름과 별개.

#### 체인 B: Watchlist → WatchlistItem → CorrelationData (graph_analysis)
```
User (CASCADE) → Watchlist
  └─ Watchlist (CASCADE) → WatchlistItem
       └─ Watchlist (CASCADE) → CorrelationData (3 모델: WatchlistDailyCorrelation 외)
```
🟢 Low: 단순 cascade.

#### 체인 C: ScreenerPreset → ScreenerAlert → AlertHistory (3단계 + SET_NULL)
```
User (CASCADE) → ScreenerPreset
ScreenerPreset (SET_NULL) ↘ ScreenerAlert
                            └─ ScreenerAlert (CASCADE) → AlertHistory
```
✅ 정상 패턴: preset이 사라져도 alert는 `filters_json`으로 작동.

#### 체인 D: SEC pipeline (RawDocumentStore 중심)
```
Stock (CASCADE) → RawDocumentStore (각 SEC 10-K)
  ├─ RawDocumentStore (CASCADE) → SupplyChainEvidence
  ├─ RawDocumentStore (CASCADE) → BusinessModelSnapshot
  │    └─ BusinessModelSnapshot (CASCADE) → BusinessModelEvidence
  └─ RawDocumentStore (CASCADE) → FilingProcessLog (가정 - 미확인)
```
🟡 Medium: Stock 삭제 시(만약 PROTECT 우회된다면) SEC 파이프라인 결과물 전부 소실. 또한 RawDocumentStore는 Neo4j와 동기화되지 않으므로 PG 삭제 시 Neo4j edge가 고아가 됨 — **`sync_dirty_to_neo4j`는 dirty=True인 row만 반영**하므로 삭제는 전파되지 않음.

#### 체인 E: thesis 가설 통제실
```
User (CASCADE) → Thesis
  ├─ Thesis (CASCADE) → ThesisPremise, ThesisIndicator, ThesisSnapshot, ThesisCommunity
  ├─ Thesis (CASCADE) → KeywordCache (thesis/models/keyword.py)
  └─ Thesis (CASCADE) → LearningOutcome (thesis/models/learning.py 5곳)
```
🟢 Low: 정상.

---

## Neo4j 동기화

### 1. neo4j_dirty 플래그 패턴 — 두 곳 (구현 차이 존재)

#### A. `sec_pipeline/SupplyChainEvidence` (PR-9)
- 모델 정의 (`models.py:99-100`): `neo4j_dirty = BooleanField(default=True)` + `neo4j_synced_at = DateTimeField`
- **단일 플래그 정책 (코멘트 명시)**: `synced_to_neo4j` 필드 금지 — neo4j_dirty만 사용
- 자동 갱신: `signals.py:52`에서 evidence 매칭 시 `update(target_company=..., neo4j_dirty=True)` 명시
- 동기화: `tasks.py:362-445` `sync_dirty_to_neo4j` 태스크
  - Phase A: `select_for_update(skip_locked=True)` 500건 배치
  - Phase B: Neo4j DELETE 기존 + CREATE 동적 타입 (RELATED_TO 폐기 + KNOWN_TYPES 6종)
  - Phase C: 성공한 id만 `update(neo4j_dirty=False, neo4j_synced_at=now)`
- 재시도: `@shared_task(max_retries=1, soft_time_limit=300, time_limit=360)` — 1회만 재시도, 부분 실패는 다음 주기로 이월

#### B. `chainsight/RelationConfidence` (PR-3)
- 모델 정의 (`relation_discovery.py:130-135`): **이중 플래그**
  - `synced_to_neo4j = BooleanField(default=False)` (레거시)
  - `neo4j_dirty = BooleanField(default=True, db_index=True)` (신규)
- 🔴 자동 갱신 부작용: `save()` 오버라이드(`L148-161`)에서 **무조건 `neo4j_dirty=True` 강제** — 정상 갱신 후에도 다시 dirty가 됨
  - 결과: sync 직후 어떤 필드든 `save()`가 호출되면 즉시 다시 동기화 대상으로 마킹
  - 코멘트 (`L159`): "bulk_update에서는 save() 미호출되므로 수동 관리 필요" — 🟡 Medium 위험: bulk_update 사용자가 dirty 플래그 관리 누락 가능
- 동기화: `services/neo4j_sync.py:22-54` `sync_dirty_relations`
  - confirmed/probable/market-weak → `_upsert_edge`
  - 그 외 → `_delete_edge`
  - 성공 시: `update(neo4j_dirty=False, synced_to_neo4j=True, neo4j_synced_at=now)` — **두 플래그 동시 갱신** (save() 사용 금지: dirty 재설정 방지)
- 재시도: `@shared_task(max_retries=2, default_retry_delay=60)` (`tasks/neo4j_dirty_sync_tasks.py:14`)

### 2. 동기화 실패 시 재시도 메커니즘

| 메커니즘 | sec_pipeline | chainsight |
|---|---|---|
| Celery `max_retries` | 1 | 2 |
| 부분 실패 처리 | `synced_ids`만 dirty=False, 나머지는 자동 이월 | 동일 (per-record try/except, `synced_pks`만 갱신) |
| Edge 삭제 실패 | `pass` + `logger.warning` (`tasks.py:411`) | `pass` + `logger.warning` (`neo4j_sync.py:91`) |
| Edge 생성 실패 | `synced_ids`에서 누락 → 다음 주기 재시도 | 동일 |
| 트랜잭션 격리 | Phase A에서만 `transaction.atomic` + `select_for_update(skip_locked=True)` | ❌ 없음 — 단순 `iterator(chunk_size=100)` |

🟡 Medium: chainsight는 select_for_update 미사용 → **동일 dirty row를 두 워커가 동시 sync 시도 시 Neo4j upsert 중복 호출**. Neo4j 측 멱등성에 의존.

### 3. PG ↔ Neo4j 불일치 감지 방법

| 방향 | 감지 로직 | 위치 | 평가 |
|---|---|---|---|
| **PG dirty 적체** (PG → Neo4j 미반영) | dirty=True인 매칭된 evidence count > 50 시 알림 | `sec_pipeline/quality_checks.py:90-97` | ✅ 임계값 알림만, 자동 복구는 다음 sync 주기 |
| **PG dirty 적체** (chainsight) | ❌ 없음 | - | 🔴 High: 모니터링 부재 |
| **PG → Neo4j 누락** (sync는 됐지만 Neo4j에 없는 경우) | ❌ 없음 | - | 🔴 High: edge 부재 검증 로직 없음 |
| **Neo4j → PG 고아 노드** | NewsEvent 한정만 | `news/services/news_neo4j_sync.py:700` | ⚠️ Stock/Relation 노드는 미커버 |
| **양방향 cardinality** | ❌ 없음 | - | 🔴 High: PG row 수 vs Neo4j edge 수 비교 안 함 |

🔴 High 위험 시나리오:
- Stock CASCADE로 PG의 `SupplyChainEvidence`가 삭제되더라도, 이미 `neo4j_dirty=False`로 sync된 Neo4j edge는 **삭제 신호 없음**.
- `sec_pipeline/tasks.py:362-445`의 sync는 dirty=True인 신규/수정 row만 처리 → **삭제 전파 누락**.
- 운영상 Stock 삭제가 사실상 불가능(PROTECT)하므로 현재까지는 노출 안 됐을 가능성.

### 4. 레거시 정리 흔적

- `chainsight/tasks/sync_tasks.py:163`: `MATCH ()-[r:RELATED_TO]-() DELETE r` 1회 정리 (캐시 키 `chainsight:related_to_cleanup_v1`, 365일 TTL)
- `tasks.py:148-167`에서 한 번만 실행 후 모든 confirmed/probable RC를 `synced_to_neo4j=False, neo4j_dirty=True`로 리셋 → 동적 타입으로 재생성 유도
- 🟢 Low: 의도된 마이그레이션, 단발성

---

## Unique 제약조건

### 1. `unique_together` / `UniqueConstraint` 분포 — 50+ 곳

#### 핵심 unique_together (앱별 대표)

| 앱 | 모델 | 제약 | 비고 |
|---|---|---|---|
| stocks | `DailyPrice`, `WeeklyPrice` | `(stock, date)` | `to_field='symbol'` |
| stocks | `IncomeStatement`, `BalanceSheet`, `CashFlow` | `(stock, period_type, fiscal_year, fiscal_quarter)` | |
| stocks | `EODSignal` | `(stock, signal_date, signal_tag)` | |
| users | `Portfolio`, `WatchlistItem` | `(user, stock)`, `(watchlist, stock)` | |
| users | `UserInterest` | `(user, interest_type, value)` | |
| serverless | `MarketMover`, `StockKeyword`, `SectorBreadth`, `CorporateAction`, `StockRelationship`, `ChainSightStock`, `ETFHolding`, `ThemeMatch`, `RegulatoryEvent`, `InstitutionalHolding` | 11개 | mover_type/date 등 키 다양 |
| serverless | `LLMExtractedRelation` (마이그 0011) | `(source, target, relation_type, source_id)` | |
| chainsight | `ChainNewsEvent` | `(source, source_id)` | |
| chainsight | `RelationConfidence` | `(symbol_a, symbol_b, relation_type)` | undirected normalize 필요 |
| chainsight | `RelationDiscovery` | `(symbol_a, symbol_b)` + `(symbol_a, symbol_b, period)` | |
| chainsight | `CompanyEventReaction` | `(symbol, event_type)` | |
| validation | `CompanyMetricLatest` | `(symbol, metric_code)` | |
| validation | `CategoryScore`, `CompanyBenchmarkDelta` | preset_key 포함 4-튜플 | |
| validation | `PeerPreset`, `UserPeerPreference` | `(symbol, preset_key)`, `(user, symbol)` | |
| metrics | `CompanyMetricSnapshot` | `(symbol, fiscal_year, metric_code)` | |
| metrics | `IndustryMetricBenchmark`, `PeerMetricBenchmark` | preset_key 포함 4-튜플 | |
| portfolio | `WalletHolding`, `PercentileCache`, `DiagnosticCard.priority`, `LLMComment` | `UniqueConstraint` 사용 | |
| thesis | `ThesisCommunity`, `ThesisIndicator.asof`, `ThesisSnapshot`, `KeywordCache` | 4개 | |
| sec_pipeline | `CompanyAlias` | `(alias, context_sector)` | sector 폴백 핵심 |
| rag_analysis | `BasketItem` | `(basket, item_type, reference_id)` | |
| graph_analysis | 4모델 | watchlist+stock+date 조합 | |
| macro | `EconomicIndicator`, `MarketIndexPrice`, `MacroCorrelation`, `IndicatorImpact` | 4개 | |
| news | `NewsSymbol`, `SentimentHistory` | `(news, symbol)`, `(symbol, date)` | |

### 2. `update_or_create` 사용 + race condition 가능성 — 49개 파일에 분포

🟡 Medium 위험 — Celery 동시 실행 환경에서 `IntegrityError`로 실패할 수 있는 위치:

| 파일 | 줄 | 모델 | unique 키 | race 가능성 |
|---|---|---|---|---|
| `sec_pipeline/tasks.py` | 120 | `RawDocumentStore` | (가정: cik+accession_no) | 🟡 같은 SEC 문서 동시 수집 시 |
| `sec_pipeline/tasks.py` | 314 | `RelationConfidence` | `(symbol_a, symbol_b, relation_type)` | 🟡 evidence-to-relation seed 동시 실행 시 |
| `serverless/tasks.py` | 393 | `StockKeyword` | `(symbol, date)` | 🟡 키워드 생성 Beat 중복 트리거 |
| `serverless/tasks.py` | 1425 | `StockRelationship` | `(source, target, type)` | 🟡 LLM 관계 추출 동시 실행 |
| `news/tasks.py` | 297 | `SentimentHistory` | `(symbol, date)` | 🟢 일별 호출 단발성 |
| `macro/tasks.py` | 104 | `MarketIndexPrice` | `(index, date)` | 🟢 일별 |
| `macro/tasks.py` | 174 | `EconomicEvent` | (FK related_indicator) | 🟡 계산기 카운트 충돌 |
| `stocks/tasks.py` | 99 | `WeeklyPrice` | `(stock, date)` | 🟢 단발성 |
| `stocks/tasks.py` | 649 | `SignalAccuracy` | (가정: signal+date) | 🟢 |

**완화 패턴**:
- Django `update_or_create`는 내부에서 `try/except IntegrityError` + `select_for_update`(상위에서 atomic block 시) 사용. 그러나 **외부 atomic block이 없으면** 동시 두 워커가 동일 키로 `INSERT` 시도 시 한 쪽이 IntegrityError로 실패.
- Celery 락(`cache.add`)이 호출 측에서 적용되는 경우는 미확인. 적용 권장.

### 3. `unique_together` + ArrayField/JSONField 검증 부재

- `chainsight/ChainNewsEvent.co_mentioned_symbols` (ArrayField) — unique 제약 없음. 동일 기사를 두 채널에서 받으면 `(source, source_id)` 충돌로 막히지만, 그 이전 단계의 dedup은 `is_duplicate` 플래그에 의존.
- `thesis/Thesis.premise_universe_ids/indicator_universe_ids` (JSONField, default=list) — 중복 ID 검증 로직 모델 레벨에서는 없음.

### 4. Migration 추적

- `validation/migrations/0004_alter_categorysignal_unique_together_and_more.py`: 마이그레이션 중 `unique_together=set()` → 새 4-튜플로 교체 (preset_key 도입). 이전 데이터의 unique 제약 일시 해제 → 마이그레이션 직후 중복 가능성 검증 필요.
- `metrics/migrations/0006`: PeerMetricBenchmark unique 변경 (preset_key 추가). 동일 패턴.

🟡 Medium: 두 마이그레이션 모두 unique 변경 시 **데이터 백필 + duplicate cleanup 단계가 마이그레이션 안에 포함되었는지 미확인**. 운영 마이그 기록 검토 권장.

---

## 부록: 사용자 사전 파악 vs 실제 측정

| 항목 | 사용자 입력 | 실제 측정 | 차이 |
|---|---|---|---|
| SET_NULL 위치 | 7곳, 3개 파일 | 16곳, 9개 파일 | thesis/portfolio/macro/chainsight 누락 |
| CASCADE 위치 | 37곳, 7개 파일 | 80+ 곳, 15개 파일 | thesis/metrics/validation/chainsight/portfolio/macro 누락 |
| PROTECT 위치 | (언급 없음) | 6곳, 3개 파일 (portfolio 4, metrics 1, chainsight 1) | 🔴 가장 중요한 정책 누락 |

> 권장: 다음 감사 시 `on_delete=models.PROTECT` 도 사전 파악 명령에 포함. 이 정책이 Stock 삭제 가능성을 결정하는 핵심.
