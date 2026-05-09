# 데이터 무결성 감사 보고서

- 감사일: 2026-05-09
- 범위: 전체 Django 앱 (`stocks/`, `users/`, `portfolio/`, `thesis/`, `chainsight/`, `sec_pipeline/`, `serverless/`, `rag_analysis/`, `macro/`, `marketpulse/`, `validation/`, `metrics/`, `graph_analysis/`, `news/`)
- 모드: 읽기 전용 (코드 수정 없음)
- 사전 grep 추정치 vs 실측치
  - SET_NULL: 추정 7건 → **실측 17건** (10개 파일)
  - CASCADE: 추정 37건 → **실측 90+건** (20개 파일)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 영역 | 이슈 수 | 핵심 |
|--------|------|---------|------|
| 🔴 P0 | FK orphan 정리 부재 | **3** | SET_NULL 17건 전부 orphan 감지·정리 로직 없음 |
| 🔴 P0 | Stock CASCADE 폭발 반경 | **1** | Stock 1행 삭제 시 30+ 자식 모델, 4단계 깊이 연쇄 |
| 🔴 P0 | Neo4j↔PG 불일치 감지 부재 | **2** | chainsight는 dirty 카운트만, 역방향 검증 없음 |
| 🟠 P1 | update_or_create race | **2** | 18곳 사용 중 transaction.atomic 미사용 다수 |
| 🟠 P1 | RawDocumentStore 삭제 시 BMS/SCE 동시 손실 | **1** | 양쪽 모두 CASCADE → 원본 문서 정리=사업모델 스냅샷 소실 |
| 🟡 P2 | unique_together 적절성 | **1** | 80+건 강력 보장. update_or_create와 키 정합성 OK |
| 🟡 P2 | duplicate_of self-FK SET_NULL | **1** | ChainNewsEvent 자기참조 — 안전 패턴 |
| ✅ OK | unique 제약 커버리지 | - | 모든 핵심 시계열/스냅샷 테이블에 unique_together 존재 |

**우선 조치 권고**: Neo4j↔PG 역방향 정합성 체커 + Stock CASCADE 사전 영향 평가 커맨드 + SET_NULL FK 주기적 orphan 카운트.

---

## FK orphan 위험

### SET_NULL 사용 인벤토리 (17건, 10개 파일)

| # | 파일 | 라인 | 필드 | 부모 → 자식 | orphan 발생 시 영향 |
|---|------|------|------|-------------|---------------------|
| 1 | rag_analysis/models.py | 145 | `basket` | DataBasket → AnalysisSession | 세션 컨텍스트 소실, 탐험 경로 무의미화 |
| 2 | rag_analysis/models.py | 256 | `session` | AnalysisSession → UsageLog | 비용 추적 가능, 세션 컨텍스트 소실 |
| 3 | rag_analysis/models.py | 263 | `message` | AnalysisMessage → UsageLog | 메시지별 토큰 추적 단절 |
| 4 | serverless/models.py | 660 | `preset` | ScreenerPreset → ScreenerAlert | 알림이 `filters_json` fallback으로만 동작 |
| 5 | serverless/models.py | 808 | `user` | User → InvestmentThesis | 유저 삭제 후에도 테제 보존 (의도적) |
| 6 | serverless/models.py | 1409 | `user` | User → AdminActionLog | 감사 로그 보존 (의도적) |
| 7 | chainsight/models/news_event.py | 54 | `duplicate_of` | self → ChainNewsEvent | 중복 클러스터 해체. 안전. |
| 8 | macro/models/indicators.py | 298 | `related_indicator` | EconomicIndicator → EconomicEvent | 이벤트의 지표 연결 끊김 |
| 9 | portfolio/models.py | 327 | `wallet_snapshot_at_execution` | WalletSnapshot → AnalysisRun | RV4-b 시점 스냅샷 소실 — 재현 불가능 |
| 10 | portfolio/models.py | 732 | `analysis_run` | AnalysisRun → ChatSession | 대화-실행 연결 단절 |
| 11 | portfolio/models.py | 831 | `context_analysis_run` | AnalysisRun → Decision | 의사결정 컨텍스트 소실 |
| 12 | thesis/models/monitoring.py | 66 | `indicator` | ThesisIndicator → ThesisAlert | 알림의 지표 메타 소실 |
| 13 | thesis/models/indicator.py | 15 | `premise` | ThesisPremise → ThesisIndicator | 지표가 어떤 전제에 종속되었는지 단절 |
| 14 | thesis/models/thesis.py | 70 | `source_news` | NewsArticle → Thesis | 뉴스 출처 단절 |
| 15 | thesis/models/thesis.py | 77 | `copied_from` | self → Thesis | 카피 체인 단절. 안전. |
| 16 | sec_pipeline/models.py | 86 | `target_company` | Stock → SupplyChainEvidence | **상대 기업 식별 정보 소실 → Neo4j sync 누락** |
| 17 | marketpulse/models/anomaly.py | 25 | `paired_news` | MarketPulseNews → AnomalySignalLog | 이상 신호와 짝 뉴스 단절 |

### Orphan 정리 로직 존재 여부

**검색 결과**: `orphan|cleanup_dangling|cleanup_orphan` grep으로 발견된 정리 로직은 **단 1곳**.

```
news/services/news_neo4j_sync.py:700  # Neo4j 그래프 측 NewsEvent 노드 정리
```

- **PostgreSQL 측 SET_NULL 후 NULL 레코드 정리/감지/모니터링 로직: 0건**
- 17건 SET_NULL FK 모두 **NULL이 영구 누적되어도 감지 메커니즘 없음**
- 특히 위험한 케이스:
  - **#16 `target_company`**: NULL이 되면 `sec_pipeline/tasks.py:365` 의 `filter(target_company__isnull=False)` 조건에 의해 Neo4j 동기화에서 영구 제외 → 증거(`SupplyChainEvidence`)는 살아있지만 그래프에 반영 안 됨
  - **#9 `wallet_snapshot_at_execution`**: RV4-b 스냅샷이 NULL이 되면 AnalysisRun의 재현성 손실 — `is_finalized=True` 가드와 충돌
  - **#13 `premise`**: ThesisIndicator가 어느 전제(premise)에 속했는지 사라지면 `premise_universe_ids`/`indicator_universe_ids` 정합성 깨짐 (v2.3.2 수학 모델 영향)

### 권고

1. **Periodic NULL audit**: Celery Beat `daily` 잡으로 17건 SET_NULL FK의 NULL 카운트를 메트릭으로 export
2. **Orphan 임계값 알림**: 신규 NULL 발생률이 평소보다 N배 → Slack/Email 통보
3. **`target_company__isnull=True` 별도 처리 큐**: ticker_matcher 재시도 사이클 또는 admin 검토 큐로 분리

---

## CASCADE 체인

### CASCADE 전수 (90+건, 20개 파일)

영역별 압축:

| 앱 | CASCADE 건수 | 주요 chain root |
|----|--------------|----------------|
| portfolio | 12 | User, Portfolio, AnalysisRun, Wallet |
| thesis | 12 | User, Thesis, ThesisIndicator |
| chainsight | 8 | Stock |
| graph_analysis | 8 | Watchlist, Stock |
| stocks | 6 | Stock |
| validation | 7 | Stock, MetricDefinition, User |
| serverless | 4 | User, Stock |
| sec_pipeline | 5 | Stock, RawDocumentStore, BusinessModelSnapshot |
| rag_analysis | 5 | User, DataBasket, AnalysisSession |
| metrics | 4 | Stock, MetricDefinition |
| macro | 5 | EconomicIndicator, MarketIndex |
| users | 5 | User, Watchlist, Stock |
| news | 2 | NewsArticle, Stock |
| marketpulse | 2 | MarketPulseNews, MarketPulseSnapshot |

### 3단계 이상 연쇄 삭제 chain (검출)

#### Chain A: User 삭제 → 4단계 연쇄
```
User (auth_user)
 ├─CASCADE→ Portfolio (users, portfolio)            [users:27, portfolio:55]
 │           └─CASCADE→ AnalysisRun (portfolio:292)
 │                       ├─CASCADE→ MetricResult (portfolio:388)
 │                       ├─CASCADE→ DiagnosticCard (portfolio:483)
 │                       ├─CASCADE→ AnalysisComment (portfolio:561)
 │                       └─SET_NULL→ ChatSession.analysis_run (portfolio:732)
 ├─CASCADE→ ChatSession (portfolio:727)
 │           └─CASCADE→ Message (portfolio:772)
 ├─CASCADE→ Decision (portfolio:821)
 ├─CASCADE→ Watchlist (users:171)
 │           └─CASCADE→ WatchlistItem (users:197)
 ├─CASCADE→ UserInterest (users:256)
 ├─CASCADE→ Thesis (thesis/thesis:11)
 │           ├─CASCADE→ ThesisPremise (thesis/thesis:146)
 │           ├─CASCADE→ ThesisIndicator (thesis/indicator:10)
 │           │           ├─CASCADE→ ThesisIndicatorSnapshot (thesis/indicator:124)
 │           │           ├─CASCADE→ ThesisLearning (thesis/learning:74,79,102)
 │           │           └─SET_NULL→ ThesisAlert.indicator (thesis/monitoring:66)
 │           └─CASCADE→ ThesisSnapshot (thesis/monitoring:10)
 ├─CASCADE→ ScreenerAlert (serverless:647)
 ├─CASCADE→ AnalysisSession (rag_analysis:138)
 │           └─CASCADE→ AnalysisMessage (rag_analysis:194)
 ├─CASCADE→ UsageLog (rag_analysis:249)
 └─CASCADE→ DataBasket (rag_analysis:16)
             └─CASCADE→ BasketItem (rag_analysis:78)
```
**최대 깊이**: 4단계 (User → Portfolio → AnalysisRun → MetricResult/Comment/Card)
**자식 모델 수**: 18+ 직접/간접

#### Chain B: Stock 삭제 — 가장 광범위한 영향
다음은 **'Stock' FK CASCADE를 가진 모델만** 정리:

```
Stock (stocks_stock, PK=symbol)
 ├─CASCADE→ DailyPrice              (stocks:133)
 ├─CASCADE→ WeeklyPrice             (stocks:244)
 ├─OneToOne CASCADE→ KoreanOverview (stocks:699)
 ├─CASCADE→ IncomeStatement         (stocks:756)
 ├─CASCADE→ BalanceSheet/CashFlow   (stocks:801)
 ├─CASCADE→ EODSignal/Snapshot      (stocks:888)
 ├─CASCADE→ Portfolio.stock         (users:28)
 ├─CASCADE→ WatchlistItem.stock     (users:198)
 ├─CASCADE→ chainsight.CompanyChainProfile      (chain_profile:12)
 ├─CASCADE→ chainsight.CompanyNarrativeTag      (narrative_tag:22)
 ├─CASCADE→ chainsight.CompanySensitivityProfile(sensitivity:17)
 ├─CASCADE→ chainsight.CompanyGrowthStage       (growth_stage:18)
 ├─CASCADE→ chainsight.CompanyEventReaction     (event_reaction:17)
 ├─CASCADE→ chainsight.CompanyCapitalDNA        (capital_dna:22)
 ├─CASCADE→ chainsight.CompanyRevenueStructure  (revenue_structure:20)
 ├─CASCADE→ chainsight.CompanyInsiderSignal     (insider_signal:27)
 ├─PROTECT→ chainsight.ChainNewsEvent           (news_event:23)  ← 삭제 차단
 ├─CASCADE→ sec_pipeline.RawDocumentStore.stock (sec_pipeline:25)
 │           ├─CASCADE→ SupplyChainEvidence.source_document  (sec_pipeline:78)
 │           └─CASCADE→ BusinessModelSnapshot.source_document(sec_pipeline:165)
 ├─CASCADE→ sec_pipeline.SupplyChainEvidence.source_company  (sec_pipeline:82)
 ├─SET_NULL→ sec_pipeline.SupplyChainEvidence.target_company (sec_pipeline:86)
 ├─CASCADE→ sec_pipeline.BusinessModelSnapshot.symbol        (sec_pipeline:161)
 ├─CASCADE→ validation.PeerPreset.symbol           (peer_preset:20)
 ├─CASCADE→ validation.UserPeerPreference.symbol   (peer_preset:50)
 ├─CASCADE→ validation.ValidationNewsSummary       (news_summary:7)
 ├─CASCADE→ validation.CompanyMetricLatest         (metric_latest:7)
 ├─CASCADE→ validation.CompanyBenchmarkDelta       (benchmark_delta:7)
 ├─CASCADE→ validation.CategorySignal              (category_score:20)
 ├─CASCADE→ metrics.CompanyMetricSnapshot          (metric_snapshot:19) — PROTECT 대상은 MetricDefinition
 ├─CASCADE→ portfolio.WalletHolding.stock          (portfolio:163)
 ├─CASCADE→ portfolio.PercentileCache 등 (4건)
 ├─CASCADE→ thesis.ThesisIndicator.symbol(추정) — 직접 FK 검증 필요
 ├─CASCADE→ graph_analysis.NodeMetadata 등         (graph_analysis:178,185,291,334)
 └─PROTECT→ chainsight.ChainNewsEvent             ← 삭제 차단 동작
```

- **Stock FK 직접 자식 모델: 30+ 클래스** (PROTECT 1건 포함)
- `to_field='symbol'` 사용 → symbol 변경(예: 합병 후 ticker 교체) 시 모든 자식 cascade 업데이트 필요
- `chainsight.ChainNewsEvent`가 **PROTECT** → Stock 삭제 자체가 차단됨
  - 결과적으로 운영상 Stock 삭제는 **사실상 불가능** (PROTECT가 안전망)
  - 그러나 `delete()` 시도 시 `ProtectedError` 핸들러가 admin 외에 없음 → 사용자 경험 저하

#### Chain C: RawDocumentStore 삭제 (양 child 동시 손실)
```
RawDocumentStore
 ├─CASCADE→ SupplyChainEvidence (sec_pipeline:78)  → Neo4j sync 영향
 └─CASCADE→ BusinessModelSnapshot (sec_pipeline:165)
```
원본 10-K 문서 정리 시 **공급망 증거**와 **비즈니스 모델 스냅샷**이 동시 소실. 
- BusinessModelSnapshot에는 `direct_customer_contact`, `recurring_revenue_signal` 등 **재계산 불가능한 LLM 추출 결과** 포함.
- 권고: RawDocumentStore에 soft-delete (`is_archived` 필드) 패턴 또는 `PROTECT` 전환 검토.

#### Chain D: Watchlist → 그래프 분석 chain
```
Watchlist
 └─CASCADE→ graph_analysis.WatchlistDailyMetric / NodeMetadata / EdgeMetadata 등 (graph_analysis 내 다수)
```
- graph_analysis는 8건 CASCADE 전부 Watchlist/Stock 종속.
- Watchlist 삭제 시 분석 결과 전체 소실 — 의도적인 듯 하나 백업 메커니즘 없음.

### 위험 요약

| 폭발 반경 순위 | 부모 모델 | 직접 자식 | 깊이 |
|----------------|-----------|----------|------|
| 1 | Stock | 30+ | 3단계 (Stock→RawDoc→SCE/BMS) |
| 2 | User | 18+ | 4단계 (User→Portfolio→AnalysisRun→MetricResult) |
| 3 | Thesis | 5 | 3단계 (Thesis→ThesisIndicator→ThesisIndicatorSnapshot/Learning) |
| 4 | RawDocumentStore | 2 | 1단계 — 그러나 LLM 산출물 손실 |
| 5 | Watchlist | 5+ | 1단계 — graph_analysis 전체 |

### 권고

1. **사전 영향 평가 커맨드**: `python manage.py impact_report --model Stock --pk AAPL` — 삭제 시 cascade 영향 행수 출력
2. **Stock PROTECT 일관화**: ChainNewsEvent만 PROTECT인 점 → 다른 정량 데이터(metrics, validation)도 PROTECT 검토
3. **RawDocumentStore soft-delete**: LLM 추출 결과 보호
4. **AnalysisRun.is_finalized 가드 확장**: User CASCADE 시 finalized run은 별도 archive 후 익명화

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 사용 현황

3개 모델에서 `neo4j_dirty: BooleanField(default=True, db_index=True)` 채택 (audit P0 #9, 2026-04-29 통일):

| 모델 | 파일 | 방향 | 동기화 태스크 |
|------|------|------|--------------|
| `chainsight.CompanyChainProfile` | chainsight/models/chain_profile.py:65 | True=동기화 필요 | `chainsight.tasks.sync_tasks.sync_profiles_to_neo4j` |
| `chainsight.RelationConfidence` | chainsight/models/relation_discovery.py:130 | True=동기화 필요 | `chainsight.tasks.sync_tasks.sync_relations_to_neo4j` → `services.neo4j_sync.sync_dirty_relations` |
| `sec_pipeline.SupplyChainEvidence` | sec_pipeline/models.py:100 | True=동기화 필요 | `sec_pipeline.tasks.sync_dirty_to_neo4j` |

**디자인 통일성** (긍정):
- 의미 통일: `True = 동기화 필요` (이전 `synced_to_neo4j` 반전 의미와 마이그레이션 0008로 통합)
- DB 인덱스 모두 존재 (`db_index=True` 또는 `models.Index(fields=['neo4j_dirty'])`)
- `bulk_update`/`queryset.update()` 시 `save()` 미호출 → 수동 `neo4j_dirty=True` 토글 명시 (relation_tasks.py:382-402)
- `update_or_create`는 `save()` 호출 → `neo4j_dirty` 자동 True (의도된 패턴)

### 동기화 실패 시 재시도 메커니즘

| 태스크 | max_retries | 실패 시 동작 |
|--------|-------------|--------------|
| `chainsight.sync_profiles_to_neo4j` | **1** | 개별 profile try/except, 실패 시 `neo4j_dirty=True` 잔류 → 다음 sync 사이클에 재시도 |
| `chainsight.sync_relations_to_neo4j` (위임 → `sync_dirty_relations`) | **1** | 동일 패턴, 실패 row는 `synced_pks`에서 제외되어 dirty 잔류 |
| `sec_pipeline.sync_dirty_to_neo4j` | **1** | `select_for_update(skip_locked=True)` + 2-Phase + try/except per row, 실패 시 `synced_ids`에서 제외 |

**강점**:
- `select_for_update(skip_locked=True)` (sec_pipeline) → 동시 실행 안전
- Per-row try/except → 일부 실패가 전체 배치 실패로 번지지 않음
- 다음 주기에 자연스럽게 재시도 (dirty 플래그 기반)

**약점**:
1. `max_retries=1`이지만 `bind=True`만 있고 `self.retry()` 호출 코드 없음 → Celery 재시도 자체는 비활성. 다음 Beat 주기에만 의존.
2. **재시도 카운터 없음** — 같은 row가 영원히 dirty=True로 잔류해도 알 수 없음. "왜 안 동기화 되는가" 추적 불가.
3. `_delete_edge` 실패 시 `logger.warning`만 — 그러나 `synced_pks.append(rc.pk)`는 try 블록 안 → 실패 시 dirty 유지 (정상)
4. `sync_profiles_to_neo4j`는 `save(update_fields=["neo4j_dirty","neo4j_synced_at"])`로 안전 — 그러나 `props`가 비어있어도(`if props:` 분기 없는 fallback) `neo4j_dirty=False`로 마킹됨 (line 130-138 분기) → 빈 동기화도 성공 처리되는 경계 케이스.

### PG ↔ Neo4j 불일치 감지 방법

#### 현존하는 메커니즘
- `sec_pipeline/quality_checks.py:144-148` — `neo4j_synced` (dirty=False) / `neo4j_pending` 카운트만 제공
- `sec_pipeline/intelligence.py:97-98` — 동일한 카운트 제공
- `chainsight`: 통계성 카운트만, 상세 비교 없음

#### 부재한 메커니즘 (위험)
1. **PG에는 있고 Neo4j에는 없는 케이스**:
   - dirty=False인데 실제 Neo4j에 노드/엣지가 없을 때 감지 불가
   - 예: Neo4j 컨테이너 데이터 손실 후 재시작 → PG는 "동기화됨"으로 인식, 실제 그래프는 비어 있음
   - 검증 쿼리 부재
2. **Neo4j에는 있고 PG에는 없는 케이스 (orphan 그래프)**:
   - 1회성 cleanup만 존재: `chainsight/tasks/sync_tasks.py:158` (RELATED_TO 레거시 정리)
   - news 측: `news/services/news_neo4j_sync.py:700` orphan NewsEvent 정리
   - **chainsight Stock 노드 / sec_pipeline 엣지의 정기 orphan 검출 없음**
3. **재시도 카운터/실패 이력 부재**:
   - 모델에 `sync_attempt_count`, `last_sync_error` 같은 필드 없음
   - 영구 실패 row를 알람 없이 누적 가능

### Stock 삭제 시 Neo4j 정합성

- Stock CASCADE 시 PG 측 `RelationConfidence`, `SupplyChainEvidence`, `CompanyChainProfile`이 사라짐
- 그러나 **Neo4j 노드/엣지는 자동 삭제되지 않음** (별도 `_delete_edge` 호출 필요)
- 시나리오: Stock 삭제 → PG 자식 CASCADE → 다음 sync는 dirty rows가 없어 트리거 안 됨 → **Neo4j에 zombie 노드/엣지 잔류**
- ChainNewsEvent의 PROTECT 가드가 사실상 Stock 삭제를 막고 있어 운영상 잠재 위험

### 권고

1. **양방향 reconciliation 잡** (월 1회):
   - PG `RelationConfidence(dirty=False).count()` vs Neo4j `MATCH ()-[r]-() RETURN count(r)` 비교
   - 차이 N% 이상 발생 시 알람 + 재동기화
2. **Sync 실패 추적 필드 추가**:
   - `sync_attempt_count`, `last_sync_error`, `last_sync_attempted_at`
   - N회 실패 시 quarantine 상태 → admin 검토 큐
3. **Stock 삭제 시 Neo4j 정리 signal 등록**:
   - `pre_delete` signal에서 해당 ticker 노드/엣지 삭제
   - 또는 ChainNewsEvent PROTECT 일관 적용 (현재 정책 고정 권장)
4. **빈 props 동기화 분기**: `chainsight/tasks/sync_tasks.py:130` `if props:` 체크는 있지만 빈 props도 `neo4j_dirty=False` 마킹됨 — 의도와 일치하는지 확인 필요

---

## Unique 제약조건

### 인벤토리

- `unique_together`: **80+ 건** (모델 정의 + 마이그레이션 합산)
- `UniqueConstraint`: **5건** — portfolio 4건 + (마이그레이션 내 percentile_cache 등)

#### 핵심 제약 (대표)

| 모델 | 제약 | 강도 |
|------|------|------|
| `stocks.DailyPrice` | (stock, date) | ★★★ — 시계열 핵심 |
| `stocks.WeeklyPrice` | (stock, date) | ★★★ |
| `stocks.IncomeStatement` 외 재무제표 | (stock, period_type, fiscal_year, fiscal_quarter) | ★★★ |
| `stocks.EODSignal` | (stock, signal_date, signal_tag) | ★★★ |
| `users.Portfolio` | (user, stock) | ★★ |
| `users.WatchlistItem` | (watchlist, stock) | ★★ |
| `users.UserInterest` | (user, interest_type, value) | ★★ |
| `serverless.MarketMover` | (date, mover_type, symbol) | ★★ |
| `serverless.StockKeyword` | (symbol, date) | ★★ |
| `serverless.ScreenerSectorPerformance` | (date, sector) | ★★ |
| `serverless.LLMExtractedRelation` | (source_symbol, target_symbol, relation_type, source_id) | ★★ |
| `serverless.InstitutionalHolding` | (institution_cik, stock_symbol, report_date) | ★★ |
| `chainsight.RelationConfidence` | (symbol_a, symbol_b, relation_type) | ★★★ — Neo4j 동기화 키 |
| `chainsight.PriceCoMovement` | (symbol_a, symbol_b, period) | ★★ |
| `chainsight.ChainNewsEvent` | (source, source_id) | ★★ |
| `chainsight.CompanyEventReaction` | (symbol, event_type) | ★★ |
| `metrics.CompanyMetricSnapshot` | (symbol, fiscal_year, metric_code) | ★★★ |
| `metrics.PeerMetricBenchmark` | (symbol, fiscal_year, metric_code, **preset_key**) | ★★★ — 프리셋 분기 후 4-tuple |
| `validation.CompanyBenchmarkDelta` | (symbol, fiscal_year, metric_code, preset_key) | ★★★ |
| `validation.CategorySignal` | (symbol, category, fiscal_year, preset_key) | ★★ |
| `validation.PeerPreset` | (symbol, preset_key) | ★★ |
| `validation.UserPeerPreference` | (user, symbol) | ★★ |
| `thesis.ThesisSnapshot` | (thesis, asof_date) | ★★ |
| `thesis.ThesisIndicatorSnapshot` | (indicator, asof) | ★★ |
| `thesis.ThesisKeyword` | (target, source, text) | ★ |
| `portfolio.WalletHolding` | (wallet, stock) | ★★ |
| `portfolio.UniqueConstraint(metric_id, industry_code, date)` | percentile_cache | ★★ |
| `portfolio.UniqueConstraint(analysis_run, priority)` | unique_card_priority_per_run | ★★ |
| `portfolio.UniqueConstraint(analysis_run, stock, metric_id)` | unique_comment_per_run + unique_metric_result | ★★★ |
| `marketpulse.RegimeSnapshot` | (date,) | ★★ |
| `marketpulse.MarketPulseBriefing` | (date, model_version) | ★★ |
| `macro.IndicatorValue` | (indicator, date) | ★★★ |
| `macro.IndicatorRelationship` | (indicator_a, indicator_b) | ★★ |
| `news.NewsArticleStock` | (news, symbol) | ★★ |
| `news.SymbolNewsAggregate` | (symbol, date) | ★★ |

**커버리지**: 모든 시계열·스냅샷·관계·매핑 테이블에 unique 제약 존재. 누락 없음.

### `update_or_create` 사용 현황 — race 가능성

총 **63개 파일**에서 `update_or_create` 사용. 핵심 호출 위치 평가:

| 위치 | 키 | unique 제약 일치 | transaction.atomic | race 위험 |
|------|----|---------------------|---------------------|-----------|
| `serverless/services/data_sync.py:196` | (date, mover_type, symbol) | ✅ | 미사용 | 🟡 |
| `chainsight/services/seed_selection.py:33` | (symbol) | ✅ (PK) | 미사용 | 🟢 |
| `chainsight/tasks/relation_tasks.py:179` (PriceCoMovement) | (symbol_a, symbol_b, period) | ✅ | 미사용 | 🟡 |
| `chainsight/tasks/relation_tasks.py:275` (PEER_OF) | (symbol_a, symbol_b, relation_type) | ✅ | 미사용 | 🟡 |
| `chainsight/tasks/relation_tasks.py:309` (CO_MENTIONED) | 동일 | ✅ | 미사용 | 🟡 |
| `chainsight/tasks/relation_tasks.py:343` (PRICE_CORRELATED) | 동일 | ✅ | 미사용 | 🟡 |
| `sec_pipeline/tasks.py:314` (RelationConfidence seed) | (symbol_a, symbol_b, relation_type) | ✅ | ✅ (`@shared_task` 내부에서 명시 atomic 부재이나 read-only seed 패턴) | 🟡 |
| `chainsight/tasks/profile_tasks.py` (CompanyChainProfile) | (symbol) PK | ✅ | 미사용 | 🟢 |
| `validation/services/preset_generator.py` 외 다수 | (symbol, preset_key) | ✅ | 미사용 | 🟡 |

**평가**:
- `select_for_update` 또는 `transaction.atomic` 사용처: 18곳 (전체 grep 카운트)
- `update_or_create` 사용처: 18+ 함수 (63개 파일 매칭, 중복 포함)
- **Django의 `update_or_create`는 내부적으로 `select_for_update` 미사용** → 동시 실행 시 양쪽이 INSERT 시도하면 IntegrityError 발생 가능
  - unique_together가 정의되어 있으므로 **데이터 깨짐은 없음** (DB 레벨 보호)
  - 그러나 **하나는 IntegrityError 예외 발생** → 태스크 실패 → max_retries 정책 의존
- chainsight relation_tasks 4건: Celery Beat에서 단일 워커로 순차 실행되면 문제 없음. **수동 트리거 + Beat 동시 실행 시** race 가능
- `serverless/data_sync.py:196` MarketMover: 일배치, 동시성 낮음 → 실질 위험 낮음

### 권고

1. **고빈도 update_or_create는 `transaction.atomic` 래핑**:
   - chainsight/tasks/relation_tasks.py 4건 → Celery Beat 수동 trigger 동시 실행 방어
2. **IntegrityError 핸들러 명시**:
   - `try/except IntegrityError → retry` 패턴이 표준화 안 됨. 중앙 데코레이터 도입 검토
3. **Beat 중복 실행 방지**: `marketpulse/management/commands/setup_marketpulse_beat.py` 등 Beat 등록 시 `expires` + `singleton_lock` 패턴 (Redis lock) 권장

---

## 추가 관찰

### PROTECT 사용 (7건) — 명시적 안전망
- `metrics.CompanyMetricSnapshot.metric_definition` (line 11)
- `chainsight.ChainNewsEvent.symbol` (line 23) ← Stock 삭제 차단의 사실상 게이트
- `portfolio` 4건 (90, 393, 495, 566) — preset/MetricDefinition 보호
- `marketpulse.snapshot` 1건 (line 51)

→ **MetricDefinition은 PROTECT 일관 적용** (좋은 패턴). 다른 메타데이터 모델로 확장 검토.

### 마이그레이션 0008 (chainsight) — 좋은 사례
`neo4j_synced` (반전 의미) → `neo4j_dirty` 통일. 양방향 데이터 마이그레이션 함수 정의. 다른 신규 Neo4j 모델은 처음부터 `neo4j_dirty` 패턴 따르고 있음.

---

## 최종 액션 우선순위

| P | 작업 | 영향 모델 | 예상 공수 |
|---|------|----------|----------|
| 0 | Neo4j ↔ PG 양방향 reconciliation 잡 | chainsight, sec_pipeline | 1-2일 |
| 0 | SET_NULL FK NULL 카운트 일일 메트릭 | 17건 전부 | 0.5일 |
| 0 | Stock cascade 영향 평가 management 커맨드 | Stock | 0.5일 |
| 1 | sync_attempt_count/last_sync_error 필드 추가 | 3개 모델 | 1일 |
| 1 | RawDocumentStore soft-delete 또는 PROTECT 검토 | sec_pipeline | 0.5일 + 마이그레이션 |
| 1 | chainsight relation_tasks `transaction.atomic` + Redis singleton lock | chainsight | 0.5일 |
| 2 | AnalysisRun.is_finalized → User CASCADE 시 익명화 정책 | portfolio | 1일 |
| 2 | Stock pre_delete signal로 Neo4j zombie 노드 정리 | stocks | 0.5일 |

---

## 부록: 실측 grep 결과 요약

```
SET_NULL  17 hits / 10 files
CASCADE   90+ hits / 20 files
PROTECT    7 hits / 5 files
unique_together / UniqueConstraint   80+ hits
update_or_create  63 file matches, 18+ distinct call sites
select_for_update | @transaction.atomic  18 occurrences / 11 files
neo4j_dirty 일치 모델  3개 (chainsight 2 + sec_pipeline 1)
```

(끝)
