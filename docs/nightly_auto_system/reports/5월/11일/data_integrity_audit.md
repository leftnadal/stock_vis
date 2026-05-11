# 데이터 무결성 감사 보고서

- **감사 일자**: 2026-05-11
- **저장소**: `/Users/byeongjinjeong/Desktop/stock_vis`
- **브랜치**: `fix/circuitbreaker-p0-7-call-sites`
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 범위**: FK on_delete 정책, CASCADE 체인, Neo4j ↔ PostgreSQL 동기화, Unique 제약/race condition

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 영역 |
|--------|------|----------|
| 🔴 High | 4 | Stock.delete() 시 사일런트 도미노 / SET_NULL orphan 정리 부재 / Neo4j 미스매치 추적 부재 / DataBasket.user CASCADE + BasketItem dangling |
| 🟡 Medium | 5 | update_or_create race (PG advisory lock 부재) / 자체 참조 SET_NULL (ChainNewsEvent.duplicate_of) / SignalAccuracy 외래키 유실 시 보존 정책 부재 / Watchlist 삭제 시 CorrelationMatrix·CorrelationEdge CASCADE 가시성 / Sec_pipeline.evidence target_company SET_NULL 시 매칭 큐 재처리 트리거 부재 |
| 🟢 Low | 4 | 일부 모델 update_or_create + bulk_update 혼용 시 neo4j_dirty 누락 가능 / unique_together만 사용한 모델 다수 (UniqueConstraint 미사용) / on_delete=PROTECT를 가진 모델이 운영상 삭제 차단으로 작동 / orphan 청소 cron 부재 (전체 1건 — news_neo4j_sync만 처리) |

전체 발견 사항은 다음 섹션에서 상술한다. 실제 측정 가능한 정량 수치(예: SET_NULL 후 NULL 비율)는 DB 접근이 없는 정적 코드 감사이므로 위험 패턴만 제시한다.

---

## FK orphan 위험

### 1. SET_NULL 사용처 전체 카탈로그

사전 파악에서 사용자가 언급한 "7곳 / 3개 파일"보다 실제 사용처가 훨씬 많다 (전체 17곳 / 12개 파일).

| # | 파일:라인 | 모델/필드 | 상위 객체 삭제 시 효과 | 후속 정리 로직 |
|---|---|---|---|---|
| 1 | `rag_analysis/models.py:145` | `AnalysisSession.basket` (→ DataBasket) | session.basket = NULL | ❌ 없음 |
| 2 | `rag_analysis/models.py:256` | `UsageLog.session` (→ AnalysisSession) | log.session = NULL | ❌ 없음 |
| 3 | `rag_analysis/models.py:263` | `UsageLog.user` (→ User) | log.user = NULL (감사 추적 보존 의도) | ❌ 없음 |
| 4 | `serverless/models.py:660` | `ScreenerAlert.preset` (→ ScreenerPreset) | preset 삭제 시 alert는 살아남고 `filters_json`만 남음 | ❌ 알림 동작 정의 없음 |
| 5 | `serverless/models.py:808` | `InvestmentThesis.user` (→ User) | 익명 테제로 잔존 | ❌ 표시 정책 없음 |
| 6 | `serverless/models.py:1409` | `AdminActionLog.user` (→ User) | 감사 로그 보존 의도 — OK | (의도된 보존) |
| 7 | `chainsight/models/news_event.py:54` | `ChainNewsEvent.duplicate_of` (self FK) | 중복 마스터가 삭제되면 중복 마킹만 NULL | ❌ `is_duplicate=True` 잔존 (불일치) |
| 8 | `macro/models/indicators.py:310` | `EconomicEvent.related_indicator` | indicator 삭제 시 이벤트는 살아남음 | ❌ 없음 |
| 9 | `portfolio/models.py:327` | `AnalysisRun.wallet_snapshot_at_execution` | snapshot 삭제 시 run은 보존 (의도 명시) | (의도된 보존) |
| 10 | `portfolio/models.py:732` | `ChatSession.analysis_run` | docstring에 "느슨한 연결 (SET_NULL)" 명시 | (의도된 보존) |
| 11 | `portfolio/models.py:831` | `Decision.context_analysis_run` | 결정 이력 보존 의도 | (의도된 보존) |
| 12 | `thesis/models/monitoring.py:66` | `ThesisAlert.indicator` (추정) | 지표 삭제 시 알림 잔존 | ❌ 없음 |
| 13 | `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | premise 삭제 시 지표는 보존 | ❌ premise 미연결 지표 폐기 정책 부재 |
| 14 | `thesis/models/thesis.py:70` | `Thesis.source_news` | news 삭제 시 thesis는 보존 — OK | (의도된 보존) |
| 15 | `thesis/models/thesis.py:77` | `Thesis.copied_from` (self FK) | 원본 삭제 시 복사본만 남음 — OK | (의도된 보존) |
| 16 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | 매칭된 타겟 종목 삭제 시 → NULL + 원본 name(`target_company_name`)만 잔존 | 🟡 `UnmatchedCompanyQueue` 재진입 로직 없음 |
| 17 | `marketpulse/models/anomaly.py:25` | `AnomalySignalLog.paired_news` | 페어 뉴스 삭제 시 신호 잔존 — OK | (의도된 보존) |

### 2. SET_NULL orphan 정리 로직 존재 여부

- **저장소 전체에서 "orphan" 키워드 검색 결과**: 단 1개만 식별됨
  - `news/services/news_neo4j_sync.py:700-711` — Neo4j 측 `orphaned NewsEvent nodes` 정리 (Cypher 쿼리)
- **PostgreSQL 측 NULL 잔존 레코드 정리는 어디에도 없다**. 즉:
  - 위 표의 ❌ 표시된 항목들은 `field IS NULL` 행이 무기한 누적될 수 있다.
  - 특히 위험: **#1 AnalysisSession.basket = NULL** (LLM 컨텍스트가 깨진 채로 active 세션이 남음), **#13 ThesisIndicator.premise = NULL** (지표가 어떤 가설에 종속됐는지 추적 불가).
  - **#16 SupplyChainEvidence.target_company = NULL** 은 가장 위험. SEC 10-K에서 추출한 관계 증거가 stock 삭제로 끊긴 채 `target_company_name` 문자열만 남는다. `sec_pipeline/signals.py`의 `on_unmatched_resolved`는 **NEW 매칭** 시점에만 발화하지 sock 삭제 시점에는 발화하지 않는다.

### 3. CASCADE × SET_NULL 인접 케이스 (high risk)

- **DataBasket → AnalysisSession.basket (SET_NULL)** 이지만 동일 모델 `BasketItem`은 `basket = CASCADE` (`rag_analysis/models.py:16`).
  - 결과: basket 삭제 시 `BasketItem`은 사라지고 `AnalysisSession.basket = NULL` → session에 매달린 `UsageLog`(N+1 CASCADE)는 보존되지만 어떤 basket에서 비롯되었는지 추적 불가.
  - 권장: `basket_id_snapshot` UUID 필드를 별도 보관하거나, basket 삭제를 soft-delete로 전환.

---

## CASCADE 체인

### 1. Stock 모델 — 최다 FK 참조 허브

사전 파악 head -40 제한으로 가려졌던 전체 Stock CASCADE 참조 (확인된 것만):

| 앱 | 모델 | 줄 |
|---|---|---|
| stocks | `DailyPrice.stock` | 133 |
| stocks | `WeeklyPrice.stock` | 244 |
| stocks | `StockOverviewKo.stock` (OneToOne) | 699 |
| stocks | `EODSignal.stock` | 756 |
| stocks | `SignalAccuracy.stock` | 801 |
| stocks | `StockNews.stock` (null=True) | 888 |
| users | `PortfolioItem.stock` | 28 |
| users | `WatchlistItem.stock` | 198 |
| sec_pipeline | `RawDocumentStore.symbol` | 25 |
| sec_pipeline | `SupplyChainEvidence.source_company` | 82 |
| sec_pipeline | `BusinessModelSnapshot.symbol` | 161 |
| validation | `CompanyMetricLatest.symbol` | 7 |
| validation | `CompanyBenchmarkDelta.symbol` | 7 |
| validation | `CategoryScore.symbol` | 20 |
| validation | `NewsSummary.symbol` | 7 |
| validation | `PeerPreset.stock` × 2 | 20, 50 |
| chainsight | `CompanyChainProfile.symbol` | 12 |
| chainsight | `CompanyNarrativeTag.symbol` | 22 |
| chainsight | `CompanySensitivityProfile.symbol` | 17 |
| chainsight | `CompanyGrowthStage.symbol` | 18 |
| chainsight | `CompanyEventReaction.symbol` | 17 |
| chainsight | `CompanyCapitalDNA.symbol` | 22 |
| chainsight | `CompanyRevenueStructure.symbol` | 20 |
| chainsight | `CompanyInsiderSignal.symbol` | 27 |
| graph_analysis | `CorrelationEdge.stock_a`, `stock_b` | 75, 82 |

**Stock 1건을 삭제하면 최소 25개 테이블이 연쇄 삭제된다** (Stock은 `to_field='symbol'`이라 PG FK가 텍스트 키 기반).

### 2. 대표 3단계 이상 연쇄 삭제 시나리오

#### 시나리오 A — Stock 삭제 (가장 광범위)
```
Stock
  └─ DailyPrice (수천 ~ 수만 행)
  └─ EODSignal (300일 × 1개)
  └─ SignalAccuracy
  └─ chainsight.CompanyChainProfile (CASCADE)
        └─ (PROTECT) chainsight.CompanyChainProfile에는 자식 없음, 단 Neo4j 동기화 미발화 위험
  └─ sec_pipeline.RawDocumentStore (CASCADE)
        └─ sec_pipeline.SupplyChainEvidence (CASCADE via source_document)
              └─ chainsight.RelationConfidence (NOT FK — symbol_a/symbol_b CharField, orphan PG 행)
        └─ sec_pipeline.BusinessModelSnapshot (CASCADE)
  └─ validation.PeerPreset.stock CASCADE
        └─ validation.PeerPreset의 user는 다른 FK (CASCADE 분기)
  └─ users.PortfolioItem.stock (CASCADE → 사용자 포트폴리오 항목 사일런트 사라짐)
```
**위험**: 사용자가 보유한 `users.PortfolioItem`이 stock 삭제로 사라지면 사용자 알림 없음. `PROTECT`로 바꾸면 stock 삭제가 거부되어 안전.

#### 시나리오 B — User 삭제
```
User
  └─ users.Portfolio (CASCADE)
       └─ users.PortfolioItem (CASCADE)
  └─ users.Watchlist (CASCADE)
       └─ users.WatchlistItem (CASCADE)
       └─ graph_analysis.CorrelationMatrix (CASCADE via watchlist)
       └─ graph_analysis.CorrelationEdge (CASCADE via watchlist)
  └─ rag_analysis.DataBasket (CASCADE — 추정, 16라인)
       └─ rag_analysis.BasketItem (CASCADE)
       └─ rag_analysis.AnalysisSession (SET_NULL on basket, 단 user는 CASCADE)
            └─ rag_analysis.AnalysisMessage (CASCADE)
            └─ rag_analysis.UsageLog (CASCADE on session)
  └─ rag_analysis.AnalysisSession.user (CASCADE — 248라인 부근)
  └─ rag_analysis.UsageLog.user (SET_NULL — 감사 추적 보존)
  └─ portfolio.* (CASCADE 다수)
  └─ chainsight.SavedPath (CASCADE)
        └─ SavedPath.PathAction (CASCADE)
  └─ thesis.Thesis (CASCADE) → premises, indicators, readings 다단 CASCADE
  └─ validation.UserPeerPreference (CASCADE)
  └─ news.* (CASCADE 다수)
```
**위험**: 4단계 이상 깊이의 연쇄 삭제. PG 트랜잭션이 길어지면 `lock_timeout` 위험. 정량 측정 없음 — 모니터링 권장.

#### 시나리오 C — RawDocumentStore 삭제 (sec_pipeline 재처리 시나리오)
```
RawDocumentStore (10-K 원본)
  └─ SupplyChainEvidence (CASCADE)
        └─ chainsight.RelationConfidence: FK가 아니므로 PG는 그대로,
           Neo4j는 신호 없음 → Neo4j에 stale edge 잔존 ⚠️
  └─ BusinessModelSnapshot (CASCADE)
```
**위험**: Evidence 삭제가 Neo4j 엣지 정리 시그널을 발화하지 않는다 (`sync_dirty_to_neo4j`는 `neo4j_dirty=True`만 본다, 삭제된 행은 보이지 않음). → **Neo4j에 좀비 엣지 발생 가능**. 코드 흐름상 `delete()` 시 Neo4j 정리 훅이 없다 (`@receiver(post_delete)` 검색 결과 0).

### 3. Pre/post delete 시그널 부재

- `sec_pipeline/signals.py`: `post_save`만 정의 (UnmatchedCompanyQueue resolved 처리). `post_delete` 없음.
- `chainsight/` 전체에서 `pre_delete`/`post_delete` 시그널 정의 없음 (grep 결과 0).
- 결론: **PG에서 사라진 행이 Neo4j까지 전파되지 않는 구조적 갭** 존재.

---

## Neo4j 동기화

### 1. neo4j_dirty 플래그 사용 현황

플래그를 사용하는 모델은 3개로 통일됨 (audit P0 #9, 2026-04-29 단일화 결정).

| 모델 | 파일 | 줄 | default | db_index |
|---|---|---|---|---|
| `chainsight.CompanyChainProfile.neo4j_dirty` | `chainsight/models/chain_profile.py:65` | 65 | `True` | ✅ |
| `chainsight.RelationConfidence.neo4j_dirty` | `chainsight/models/relation_discovery.py:130` | 130 | `True` | ✅ (143) |
| `sec_pipeline.SupplyChainEvidence.neo4j_dirty` | `sec_pipeline/models.py:100` | 100 | `True` | ✅ (111) |

`synced_to_neo4j` 필드는 **이미 제거됨** (`chainsight/migrations/0008_unify_neo4j_flags.py`로 의미 통일). `neo4j_dirty=True`가 "동기화 필요"의 단일 소스.

### 2. 동기화 워커 카탈로그

| 워커 | 파일 | 트리거 | 배치 처리 | 락 |
|---|---|---|---|---|
| `sync_dirty_relations()` | `chainsight/services/neo4j_sync.py:21` | `sync_relations_to_neo4j` Celery 태스크 | `iterator(chunk_size=100)` | ❌ 없음 |
| `sync_profiles_to_neo4j` | `chainsight/tasks/sync_tasks.py:97` | Celery Beat (추정) | `iterator()` | ❌ 없음 |
| `sync_relations_to_neo4j` | `chainsight/tasks/sync_tasks.py:148` | Celery Beat | 위 `sync_dirty_relations()` 위임 | ❌ |
| `sync_dirty_to_neo4j` | `sec_pipeline/tasks.py:338` | Celery | `BATCH_SIZE=500` | ✅ `select_for_update(skip_locked=True)` (367줄) |
| `run_neo4j_dirty_sync` | `chainsight/tasks/neo4j_dirty_sync_tasks.py:15` | (alias) | — | — |

#### 패턴 비교

**sec_pipeline은 견고한 2-Phase 패턴**:
```python
# sec_pipeline/tasks.py:362-368
with transaction.atomic():
    dirty_qs = SupplyChainEvidence.objects
        .filter(neo4j_dirty=True, target_company__isnull=False)
        .select_for_update(skip_locked=True)[:BATCH_SIZE]
    rows = [...]  # dict 복사
# PG lock 해제 후 Neo4j 동기화
```
- ✅ skip_locked로 동시 워커 충돌 방지
- ✅ Neo4j 동기화 중 PG transaction 점유 없음 (lock 시간 최소화)
- ✅ Phase C에서 `queryset.update()` 사용 → `save()` 미호출 → `neo4j_dirty` 자동 재설정 회피

**chainsight는 약한 패턴**:
```python
# chainsight/services/neo4j_sync.py:32-51
for rc in dirty_qs.iterator(chunk_size=100):
    try:
        ...
        synced_pks.append(rc.pk)
    except Exception as e:
        logger.error(...)  # 실패 시 dirty=True 그대로
# 마지막에 일괄 update
```
- ❌ `select_for_update` 없음 → 동일 시점 워커 2개 실행 시 동일 행 처리 가능 (현재 Celery는 단일 워커 가정인데 명시되어 있지 않음)
- ✅ 실패한 건은 `synced_pks`에 안 들어가 다음 회차 재시도 — 재시도 메커니즘 자체는 작동

### 3. 동기화 실패 시 재시도 메커니즘

| 워커 | 재시도 | 모니터링 |
|---|---|---|
| `sync_dirty_relations` | ✅ 자연 재시도 (`neo4j_dirty=True` 잔존 → 다음 Celery 주기) | ❌ 실패 카운트 PG 미저장 |
| `sync_dirty_to_neo4j` | ✅ 동일 패턴 | ❌ `synced_at` NULL 잔존만 보임 |
| `sync_profiles_to_neo4j` | ✅ 동일 패턴 | ❌ |
| Celery task 자체 | `max_retries=1` (sync_tasks.py:14, 97, 148) | task_id 추적은 가능하나 row-level 실패 카운트 부재 |

**갭**: 재시도 횟수 추적이 없어 "영원히 dirty 상태인 행"이 식별되지 않는다. `quality_checks.py:92`에서 `neo4j_dirty=True, target_company__isnull=False` 백로그를 카운트하는 알림은 있다 (`test_neo4j_dirty_backlog_alert`로 검증됨, 임계치 50건).

### 4. PG ↔ Neo4j 불일치 감지

- **PG → Neo4j 누락 감지**: `quality_checks.py:144-146`이 sec_pipeline 한정으로 `neo4j_synced` (`neo4j_dirty=False`) vs `sync_pending` 카운트 비교.
- **Neo4j → PG orphan 감지**: `news/services/news_neo4j_sync.py:700-711`이 유일하게 Cypher `MATCH (n) WHERE NOT (...) ...` 형태로 orphan 노드 정리.
- **chainsight 관계 측 양방향 reconciliation**: ❌ 없음.
  - 즉, PG에 `RelationConfidence` 행이 삭제되었거나, 외부 도구로 Neo4j 엣지가 만들어진 경우 자동 검출 불가.
- **CompanyChainProfile**: Stock 삭제 시 CASCADE로 사라지지만, Neo4j `:Stock` 노드 속성 정리 훅 없음 → **Neo4j 측 stale 속성 잔존**.

### 5. queryset.update vs save() 인지

코드에 의식적으로 주석 처리됨:
- `chainsight/tasks/relation_tasks.py:382`: "audit P0 #9: queryset.update()는 save() 미호출 → neo4j_dirty 수동 토글"
- `chainsight/services/neo4j_sync.py:45-46`: "queryset.update() 사용 — save() 호출 금지 (dirty가 다시 True로 덮어씌워짐)"
- `chainsight/models/relation_discovery.py:157-158`: `bulk_update`에서 `neo4j_dirty=True`를 수동 세팅하도록 주석

**위험**: bulk_update를 사용하는 미래 코드에서 이 패턴을 잊으면 dirty 플래그가 토글되지 않아 동기화 누락. 정적 분석으로는 잡기 어려운 영역.

---

## Unique 제약조건

### 1. unique_together / UniqueConstraint 카탈로그

#### `unique_together` 사용처 (다수)

| 앱 | 모델 | 컬럼 |
|---|---|---|
| stocks | `DailyPrice` | (stock, date) — 185 |
| stocks | `WeeklyPrice` | (stock, date) — 214 |
| stocks | `IncomeStatement` | (stock, period_type, fiscal_year, fiscal_quarter) — 358 |
| stocks | `BalanceSheet` | 동일 패턴 — 427 |
| stocks | `CashFlow` | 동일 패턴 — 526 |
| stocks | `EODSignal` | (stock, date) — 787 |
| stocks | `SignalAccuracy` | (stock, signal_date, signal_tag) — 825 |
| users (UserInterest) | (사용자, 항목) 패턴 (256 부근) | — |
| serverless | 다수: ChainSightStock, ETFHolding 등 9건 (105, 161, 245, 562, 614, 946, 981, 1100, 1172, 1311, 1389) | — |
| metrics | `IndustryMetricBenchmark` | (industry, fiscal_year, metric_code) — 87 |
| metrics | `PeerMetricBenchmark` | (symbol, fiscal_year, metric_code, preset_key) — 138 (0006_alter에서 추가됨) |
| metrics | `CompanyMetricSnapshot` | (symbol, fiscal_year, metric_code) — 69 |
| chainsight | `ChainNewsEvent` | (source, source_id) — 63 |
| chainsight | `CompanyEventReaction` | (symbol, event_type) — 40 |
| chainsight | `RelationConfidence` | (symbol_a, symbol_b) — 24 + (symbol_a, symbol_b, relation_type) — 139 |
| chainsight | `RelationTimeSeries` | (symbol_a, symbol_b, period) — 50 |
| macro | 다수 (94, 133, 165, 257) | — |
| news | `NewsArticleSymbol` | (news, symbol) — 292 |
| rag_analysis | `BasketItem` | (basket, item_type, reference_id) — 111 |
| graph_analysis | `CorrelationMatrix` | (watchlist, date) — 51 |
| thesis | `IndicatorReading` | (indicator, asof) — 141 |

#### `UniqueConstraint` 사용처 (소수)

| 위치 | 제약 |
|---|---|
| `portfolio/models.py:438-443` | `MetricResult` 유니크: (analysis_run, stock, metric_id) `name=unique_metric_result_per_run_stock` |
| `portfolio/models.py:524-529` | `DiagnosticCard` 유니크: (analysis_run, priority) |
| `portfolio/models.py:582-587` | 추가 1건 (생략) |
| `portfolio/models.py:700-705` | 추가 1건 |

**관찰**: 신규 portfolio 앱만 `UniqueConstraint`(권장 신패턴)를 사용한다. 나머지는 모두 레거시 `unique_together`. Django 4.0+에서 `unique_together`는 deprecated 예고 — 마이그레이션 부채.

### 2. update_or_create 사용처 및 race condition 가능성

전체 `update_or_create` 호출: **121건 / 65개 파일**. 핵심 위험 사이트:

#### A. SEC pipeline (sec_pipeline/tasks.py)
- `seed_relations_to_chainsight` (314줄): `RelationConfidence.objects.update_or_create(symbol_a, symbol_b, relation_type=, defaults=...)`
- 동시 워커 2개가 같은 `(symbol_a, symbol_b, relation_type)` 키로 들어오면 PG는 `unique_together`로 IntegrityError 또는 두 번째가 update.
- **현재 mitigation**: `unique_together = ['symbol_a', 'symbol_b', 'relation_type']` (`chainsight/models/relation_discovery.py:139`) → DB 레벨에서 race는 한쪽이 IntegrityError 받음.
- **잔여 위험**: `defaults`의 일부 필드가 idempotent하지 않으면 (예: `relation_basis_summary`에 evidence_text 일부) 마지막 writer가 이김. → 이는 의도된 동작인지 불명.

#### B. chainsight aggregate_chain_profiles (chainsight/tasks/sync_tasks.py:84)
- `CompanyChainProfile.objects.update_or_create(symbol=stock, defaults=...)`
- `symbol`이 PK 또는 unique field. 동시 호출 race는 PG 레벨에서 처리됨.
- **단**: `defaults`에 `neo4j_dirty: True`가 매번 들어가므로, 동기화 직후에도 다시 dirty=True로 덮어쓸 수 있다. → **무한 dirty 루프 위험**. 단, aggregate는 주 1회(일요일 05:00)이므로 실제 발생 확률은 낮음.

#### C. validation/api/views.py (PR-prefill 등)
- `update_or_create` 1건. 사용자별 preset에 한정 → race 작음.

#### D. serverless/services/* (12개 파일)
- `KeywordService`, `SectorHeatmapService`, `SupplyChainService` 등 데이터 동기 서비스 다수.
- 핵심 패턴: `update_or_create(symbol=..., date=..., defaults={...})` + `unique_together=(symbol, date)`.
- Celery 단일 워커 가정이면 race 없음. 다중 워커 환경에서는 두 워커가 동일 (symbol, date)를 동시에 받으면 한쪽이 IntegrityError → Celery 자동 재시도가 필요.

#### E. advisory lock 부재
- `select_for_update` 사용처: **5건만** (rag_analysis 2, users 2, sec_pipeline 1).
- 즉 대부분 update_or_create는 **PG unique constraint에만 의존**한다. 이는 race 시 IntegrityError 발생 가능을 의미.
- Celery 태스크 idempotency 정책(CLAUDE.md에 명시: max_retries=3, exponential backoff)이 이 race를 완화하지만, 재시도 누적 시 비용/지연 증가 위험.

### 3. update_or_create + neo4j_dirty 자동성

- `chainsight/tasks/relation_tasks.py:291` 주석 명시: "update_or_create는 save()를 호출하므로 neo4j_dirty=True 자동."
- 즉 update_or_create는 안전. **위험은 `bulk_update` / `queryset.update()`** 사용 시.
- 현재 `queryset.update()` 호출에서 `neo4j_dirty=True` 누락 없는지 점검 결과:
  - `chainsight/tasks/relation_tasks.py:388, 395, 402`: 모두 `neo4j_dirty=True` 동반 ✅
  - `sec_pipeline/tasks.py:442` (Phase C): `neo4j_dirty=False` 명시 ✅
  - `chainsight/migrations/0008`: `neo4j_dirty=False`로 마이그레이션 ✅
- 정적 검사 통과. 미래 코드 추가 시 동일 규칙 준수 강제 메커니즘(린트/CI 체크)은 없음.

---

## 결론 및 권장 액션 (참고)

> 보고서는 읽기 전용이므로 코드 수정은 하지 않았다. 다음은 우선순위가 높은 후속 작업 후보다.

1. **🔴 High**: `SupplyChainEvidence.target_company` SET_NULL 후 `UnmatchedCompanyQueue` 재진입을 위한 후속 시그널 추가 (post_delete on Stock → re-queue).
2. **🔴 High**: `RawDocumentStore.delete()` 시 chainsight `RelationConfidence`와 Neo4j 엣지 정리 시그널/배치 추가 (현재 좀비 엣지 발생 가능).
3. **🟡 Medium**: `users.PortfolioItem.stock` 및 `WatchlistItem.stock`을 `CASCADE` → `PROTECT`로 변경 검토 (사용자 보유 자산이 사일런트 사라지는 것 방지).
4. **🟡 Medium**: chainsight 동기화 워커에 `select_for_update(skip_locked=True)` 도입 — sec_pipeline 패턴 차용.
5. **🟢 Low**: orphan PG 행(SET_NULL 후 NULL 잔존)을 주기적으로 청소하는 monitoring 태스크 추가. 특히 `AnalysisSession.basket IS NULL` 비율 추적.
6. **🟢 Low**: `unique_together` → `UniqueConstraint` 점진 마이그레이션 (Django deprecation 대응).
7. **🟢 Low**: `bulk_update`/`queryset.update` 사용 시 `neo4j_dirty=True` 누락을 잡는 CI 린트 규칙.

---

## 부록 — 감사 방법

- **정적 분석만 사용**. DB 접근 없음.
- **사용 도구**: ripgrep (Grep), file read.
- **검색 키워드**: `on_delete=models.SET_NULL`, `on_delete=models.CASCADE`, `on_delete=models.PROTECT`, `neo4j_dirty`, `unique_together`, `UniqueConstraint`, `update_or_create`, `select_for_update`, `orphan`, `post_delete`.
- **제한사항**: 실제 NULL 행 수, dirty 백로그 크기, 좀비 Neo4j 엣지 수는 측정하지 않았다. 운영 DB 접근 없이는 정량 평가 불가.
