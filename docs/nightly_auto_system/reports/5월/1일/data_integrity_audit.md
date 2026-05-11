# 데이터 무결성 감사 보고서

**감사일**: 2026-05-01
**감사 범위**: 전체 Django 앱 모델 + Neo4j 동기화 + Race Condition + Unique 제약
**감사 방식**: 정적 코드 분석 (Grep / 모델 직접 읽기) — **코드 수정 없음**
**감사자 노트**: 4월 26일 유사 감사가 있었음. 본 보고는 같은 코드베이스에 대한 최신 스냅샷이며, 4/26 이후 변경된 내용(`PROTECT` 도입 확장, Portfolio 통합)을 반영해 통계와 위험도 평가를 업데이트했다.

---

## 요약 (위험도별 이슈 수)

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 Critical | 3 | (1) **Stock(PK=symbol) 삭제 시 30+ 모델로 CASCADE 연쇄 삭제** — graph_analysis/news/portfolio/sec_pipeline/serverless/users 전부 영향, (2) **Neo4j 동기화 플래그 3중 분산** (`synced_to_neo4j` + `neo4j_dirty` + `neo4j_synced`) → DECISIONS.md "synced_to_neo4j 필드 금지" 원칙 일부 위반, (3) **PG↔Neo4j 불일치 자동 감지 메커니즘 부재** (한쪽에만 있는 노드/엣지 cross-check 없음) |
| 🟠 High | 5 | (1) **`SupplyChainEvidence.target_company` SET_NULL 후 dirty sync 필터에서 제외**되어 Neo4j에 영구 누락 가능, (2) `update_or_create` 사용처 **94곳/49파일** 모두 `select_for_update` 없이 호출 → race condition 잠재, (3) `RawDocumentStore CASCADE` → `SupplyChainEvidence` + `BusinessModelSnapshot` + `BusinessModelEvidence` 3단계 연쇄, (4) `Thesis.parent_thesis` / `copied_from` self-FK SET_NULL 후 사이클 검증 부재, (5) `chainsight.RelationConfidence.save()`가 항상 `neo4j_dirty=True`로 강제 → bulk_update 시 동기화 누락 위험 |
| 🟡 Medium | 6 | (1) `chainsight.ChainNewsEvent.duplicate_of` self FK SET_NULL 시 cluster head 손실, (2) `serverless.AdminActionLog.user` SET_NULL은 의도적이지만 감사 추적 시 user 컨텍스트 손실, (3) `rag_analysis` 3개 SET_NULL 후 UsageLog orphan(비용 추적 시 사용자 missing), (4) `update_or_create` 직후 별도 `save()` 호출(`relation_tasks` 등)로 dirty 플래그 덮어쓰기 가능, (5) FK `to_field='symbol'` 사용 시 PK 캐스케이드 거동(`stocks_stock` 직접 참조), (6) Celery 재시도 정책 `max_retries=1` (`sync_dirty_to_neo4j`, `aggregate_chain_profiles`)로 단발성 실패 보호 부족 |
| 🟢 Low | 3 | (1) `UniqueConstraint` vs `unique_together` 혼용 (마이그레이션 4건 변경 이력), (2) `FilingProcessLog.symbol`이 CharField라 Stock 삭제와 무관하게 텍스트 잔존(의도적이나 명시 필요), (3) `users.User.favorite_stock` ManyToMany는 `on_delete` 적용 안 됨(symmetric 관계상 무관) |

### FK 사용 통계 (실측)

| 정책 | 건수 | 파일 수 |
|------|------|---------|
| `CASCADE` | **93** | 31 |
| `SET_NULL` | **16** | 9 |
| `PROTECT` | **6** | 3 (`portfolio` 4건, `metrics/models/metric_snapshot` 1건, `chainsight/models/news_event` 1건) |
| `RESTRICT` / `DO_NOTHING` / `SET_DEFAULT` | **0** | 0 |

> 지시서가 표시한 "CASCADE 37건/7파일", "SET_NULL 7건/3파일"은 부분 카운트(top‑level grep `head` 결과). 전체 코드베이스 실측은 위 표대로 더 크며, 본 감사 평가는 실측치를 기준으로 한다.

---

## 1. FK Orphan 위험

### 1.1 SET_NULL 사용처 전수 (16건 / 9파일)

| 파일 | 라인 | FK 필드 | 참조 모델 | Orphan 정리 로직 |
|------|------|---------|-----------|------------------|
| `sec_pipeline/models.py` | 86 | `SupplyChainEvidence.target_company` | `stocks.Stock` | ❌ **없음** — 매칭 전 evidence는 정상 상태이므로 orphan 정의 모호 |
| `serverless/models.py` | 660 | `ScreenerAlert.preset` | `ScreenerPreset` | ❌ 없음 (preset 삭제 시 alert는 커스텀 필터로 자동 폴백) |
| `serverless/models.py` | 808 | `InvestmentThesis.user` | `users.User` | ❌ 없음 (anonymous 보존 의도) |
| `serverless/models.py` | 1409 | `AdminActionLog.user` | `users.User` | ⚠️ 의도적 (감사 로그는 user 사라져도 보존) |
| `rag_analysis/models.py` | 145 | `AnalysisSession.basket` | `DataBasket` | ❌ 없음 |
| `rag_analysis/models.py` | 256 | `UsageLog.session` | `AnalysisSession` | ❌ 없음 |
| `rag_analysis/models.py` | 263 | `UsageLog.message` | `AnalysisMessage` | ❌ 없음 |
| `portfolio/models.py` | 327 | `AnalysisRun.wallet_snapshot_at_execution` | `WalletSnapshot` | ❌ 없음 |
| `portfolio/models.py` | 732 | `ChatSession.analysis_run` | `AnalysisRun` | ❌ 없음 |
| `portfolio/models.py` | 831 | `Decision.context_analysis_run` | `AnalysisRun` | ❌ 없음 |
| `thesis/models/thesis.py` | 70 | `Thesis.source_news` | `news.NewsArticle` | ❌ 없음 |
| `thesis/models/thesis.py` | 77 | `Thesis.copied_from` (self) | `Thesis` | ❌ 없음 — self‑cycle 검증 없음 |
| `thesis/models/indicator.py` | 15 | `ThesisIndicator.premise` | `ThesisPremise` | ❌ 없음 |
| `thesis/models/monitoring.py` | 66 | `IndicatorMeasurement.indicator` | `ThesisIndicator` | ❌ 없음 |
| `macro/models/indicators.py` | 282 | `EconomicEvent.related_indicator` | `EconomicIndicator` | ❌ 없음 |
| `chainsight/models/news_event.py` | 54 | `ChainNewsEvent.duplicate_of` (self) | `ChainNewsEvent` | ❌ 없음 — cluster head 손실 위험 |

### 1.2 Orphan 정리 로직 — 결론: 부재

전체 코드베이스에서 다음 패턴을 검색했으나 **PG 측 정리 로직 없음**:
- `objects.filter(<set_null_field>__isnull=True).delete()` — 0건
- `cleanup_orphan*` / `delete_orphan*` 명령 — 0건
- 정기 cleanup Celery beat 스케줄 — 0건

**유일한 orphan 정리는 Neo4j 측**: `news/services/news_neo4j_sync.py:700` — `MATCH (n:NewsEvent) WHERE NOT (n)-[]-() DELETE n` (그래프 전용, PG와 무관).

### 1.3 🔴 Critical: `target_company SET_NULL` 후 dirty sync 영구 누락

`sec_pipeline/tasks.py:365`의 핵심 로직:
```python
dirty_qs = (
    SupplyChainEvidence.objects
    .filter(neo4j_dirty=True, target_company__isnull=False)  # ← orphan 제외
    .select_for_update(skip_locked=True)[:BATCH_SIZE]
)
```
`sec_pipeline/quality_checks.py:92`도 같은 필터(`target_company__isnull=False`)를 사용 → **orphan은 dirty count에서도 보이지 않음**.

**시나리오**: Stock 삭제 → `target_company` NULL → evidence는 `neo4j_dirty=True`이지만 sync에서 영구 제외되며, 메트릭/대시보드도 이 사실을 알리지 않음. `target_company_name`(문자열)은 보존되므로 데이터 손실은 아니지만 **Neo4j 그래프와 PG 사실 사이 영구 격차** 발생.

> **권장**: `signals.py`의 post_save에 fuzzy 재매칭 또는 `UnmatchedCompanyQueue` 자동 등록 트리거 추가. (코드 수정은 본 감사 범위 외)

### 1.4 🟠 High: `Thesis` self-FK 사이클 위험

`Thesis.copied_from` self-FK SET_NULL 시:
- A→B→A 사이클 가능 (검증 없음)
- A 삭제 → B.copied_from=NULL → B의 origin trail 손실 (사용자가 "이 가설 어디서 파생됐나?" 추적 불가)
- 동일 사용자가 자기 가설을 삭제 후 다른 가설로 파생 표시할 때 silently 끊김

---

## 2. CASCADE 체인 분석

### 2.1 CASCADE 분포 (93건 / 31파일)

| 파일 | 건수 | 비고 |
|------|------|------|
| `portfolio/models.py` | 12 | Wallet/Portfolio/AnalysisRun/Chat 트리 |
| `graph_analysis/models.py` | 8 | watchlist/stock 종속 |
| `users/models.py` | 6 | Portfolio, Watchlist, UserInterest |
| `stocks/models.py` | 6 | DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement, EODSignal, SignalAccuracy, StockOverviewKo |
| `sec_pipeline/models.py` | 6 | RawDocumentStore→Evidence/Snapshot/SubEvidence 3단 |
| `thesis/models/learning.py` | 5 | thesis 종속 학습 데이터 |
| `rag_analysis/models.py` | 5 | basket/session/message |
| `serverless/models.py` | 4 | screener/alert/etf/holding |
| `metrics/models/benchmark.py` | 4 | benchmark 트리 |
| `thesis/models/community.py` | 4 | community 트리 |
| `validation/models/peer_preset.py` | 3 | preset/preference |
| `macro/models/relationships.py` | 3 | 지표 관계 |
| chainsight 모델군 | 합계 8 | profile, sensitivity, growth, capital, narrative, insider, event, revenue, saved_path |
| 그 외 | 잔여 19 | thesis monitoring/community, news, validation snapshots 등 |

### 2.2 🔴 Critical: Stock 삭제 시 영향 범위 (가장 큰 FK 참조 대상)

`stocks.Stock`(PK=symbol, CharField)을 직접 참조하는 모델을 모두 수집:

**CASCADE (Stock 삭제 시 함께 삭제됨)**:
1. `users.Portfolio` (M2M favorite_stock 추가)
2. `users.WatchlistItem`
3. `stocks.DailyPrice`, `WeeklyPrice`, `BalanceSheet`, `IncomeStatement`, `CashFlowStatement`, `StockOverviewKo` (OneToOne), `EODSignal`, `SignalAccuracy`, `StockNews`(null 가능)
4. `sec_pipeline.RawDocumentStore`, `SupplyChainEvidence.source_company`, `BusinessModelSnapshot`
5. `chainsight.CompanyChainProfile` (OneToOne), `CompanyInsiderSignal`, `CompanyRevenueStructure`, `CompanyCapitalDNA`, `CompanyEventReaction`, `CompanyGrowthStage`, `CompanySensitivityProfile`, `CompanyNarrativeTag`
6. `validation.CompanyMetricLatest`, `CompanyBenchmarkDelta`, `CategoryScore`, `ValidationNewsSummary`, `PeerPreset`, `UserPeerPreference.symbol`
7. `serverless.ETFHolding`(간접: ETFProfile→ETFHolding이 CASCADE이며 ETFProfile.symbol은 PK)

**SET_NULL (Stock 삭제 시 NULL)**:
- `sec_pipeline.SupplyChainEvidence.target_company`

**PROTECT (Stock 삭제 차단)**:
- `portfolio.WalletHolding.stock` (라인 90)
- `portfolio.MetricResult.stock` (라인 393)
- `portfolio.StoredAnalysisStock.target_stock` (라인 495)
- `portfolio.LLMComment.stock` (라인 566)
- `metrics.CompanyMetricSnapshot.symbol` (라인 11)
- `chainsight.ChainNewsEvent.symbol` (라인 23)

**관찰**: portfolio 도메인이 Stock 삭제를 PROTECT로 차단하므로 **현실에서 Stock 직접 삭제는 사실상 불가**. 다만 PROTECT는 같은 트랜잭션에서 IntegrityError를 발생시킬 뿐, **CASCADE 그룹의 잠재적 폭발 반경은 그대로**(예: 마이그레이션/관리 명령으로 PROTECT를 우회하면 30+ 테이블이 전부 cascade).

### 2.3 🟠 High: 3단계 연쇄 — `RawDocumentStore` 삭제 시

```
RawDocumentStore (CASCADE from Stock)
  ├─ SupplyChainEvidence.source_document (CASCADE)
  └─ BusinessModelSnapshot.source_document (CASCADE)
       └─ BusinessModelEvidence.snapshot (CASCADE)
```
+ 이 evidence들의 `target_company`(SET_NULL) → Stock 삭제로 NULL이 된 다른 종목의 supply-chain 흔적이 source 삭제와 함께 동반 삭제됨.

`run_batch_and_report`(sec_pipeline/tasks.py:508)는 7200초 timeout으로 SP500 전체를 순회하므로, 단일 Stock 삭제 시 즉시는 아니지만 **다음 배치 사이클에서 누락 데이터 재수집 트리거 없음** (재수집 트리거 로직 부재).

### 2.4 CASCADE 체인 다이어그램 (요약)

```
users.User (CASCADE 받는 곳: 14개 모델)
  → Portfolio, Watchlist→WatchlistItem, UserInterest
  → Thesis → ThesisPremise → ThesisIndicator → IndicatorMeasurement
  → ChatSession → Message, Decision
  → DataBasket → BasketItem, AnalysisSession → AnalysisMessage → UsageLog
  → ScreenerAlert → AlertHistory
  → Wallet → WalletHolding, WalletSnapshot
  → analysis_runs(via Portfolio) → MetricResult(PROTECT stock), DiagnosticCard, LLMComment
  → PeerPreset(symbol+user)

stocks.Stock (CASCADE 받는 곳: 25+ 모델, 위 2.2 참조)

chainsight.SavedPath → SavedPathAction (CASCADE)

sec_pipeline.RawDocumentStore → SupplyChainEvidence + BusinessModelSnapshot → BusinessModelEvidence (3단)

graph_analysis.Watchlist → CorrelationMatrix, GraphMetadata, NetworkPosition (depth 2)
```

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 동기화 플래그 현황 — 🔴 Critical: 3중 분산

| 모델 | 필드명 | 의미 | 출처 |
|------|--------|------|------|
| `chainsight.RelationConfidence` | `synced_to_neo4j` (Bool) + `neo4j_dirty` (Bool) + `neo4j_synced_at` (DT) | 둘 다 사용 (`save()` 자동 dirty=True) | `chainsight/models/relation_discovery.py:130-135` |
| `chainsight.CompanyChainProfile` | `neo4j_synced` (Bool) + `neo4j_synced_at` (DT) | 단순 플래그 | `chainsight/models/chain_profile.py:64-65` |
| `sec_pipeline.SupplyChainEvidence` | `neo4j_dirty` (Bool) + `neo4j_synced_at` (DT) | dirty‑only 패턴 | `sec_pipeline/models.py:100-101` |

**문제**:
- `RelationConfidence`만 `synced_to_neo4j` + `neo4j_dirty`를 **모두** 보유 (DECISIONS.md / 모델 docstring에는 "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용"이라고 명시되어 있음 — `sec_pipeline/models.py:99` 주석 참조).
- `CompanyChainProfile`은 `neo4j_synced` 단일 플래그 (dirty 패턴 미적용). save() 호출 누락 시 동기화 영구 누락.
- 세 모델이 서로 다른 컨벤션을 사용 → 새 모델 추가 시 일관성 결정 비용 ↑.

### 3.2 동기화 실패 시 재시도 메커니즘

| 태스크 | 위치 | max_retries | backoff | 적용 모델 |
|--------|------|-------------|---------|-----------|
| `sync_dirty_to_neo4j` | `sec_pipeline/tasks.py:337` | **1** | default(60s) | SupplyChainEvidence |
| `aggregate_chain_profiles` | `chainsight/tasks/sync_tasks.py:14` | **1** | default | CompanyChainProfile |
| `sync_profiles_to_neo4j` | `chainsight/tasks/sync_tasks.py:96` | **1** | default | CompanyChainProfile |
| `sync_relations_to_neo4j` | `chainsight/tasks/sync_tasks.py:147` | **1** | default | RelationConfidence (dirty sync 위임) |
| `run_neo4j_dirty_sync` | `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` | **2** | 60s | RelationConfidence |
| `seed_relations_to_chainsight` | `sec_pipeline/tasks.py:281` | **1** | default | RelationConfidence (PG only) |

**평가**:
- 🟠 **High**: `max_retries=1`이 다수 → 일시적 Neo4j 연결 실패에 단발성. CLAUDE.md `coding-rules`는 "Celery 태스크: max_retries=3, exponential backoff"를 명시 → **원칙 위반**.
- ✅ Phase A/B/C 분리(`sync_dirty_to_neo4j` 라인 362~445)는 PG 트랜잭션과 Neo4j 트랜잭션을 분리해 부분 실패 시 dirty=True가 유지되도록 설계됨. **재시도 자체는 dirty 패턴 덕에 안전**.
- ⚠️ `sync_dirty_relations()` (chainsight/services/neo4j_sync.py:21)은 `try/except`로 개별 실패를 흡수만 하며, **동기화 실패 카운트가 PG에 영구 기록되지 않음** (로그만 남음). 누적 실패율 추적 불가.

### 3.3 PG↔Neo4j 불일치 감지 — 🔴 Critical 부재

검색 결과:
- PG에는 있는데 Neo4j에 없는 노드/엣지 검출 작업 — **0건**
- Neo4j에 있는데 PG에는 없는 노드/엣지 검출 작업 — **0건**
- 카운트 비교 / 해시 비교 / spot-check sampling — **0건**

존재하는 것:
- `sec_pipeline/quality_checks.py:90`: `dirty_count > 50`이면 경고 — **양적 적체**만 감지, 일치성은 미검증.
- `chainsight/tasks/sync_tasks.py:163`: `MATCH ()-[r:RELATED_TO]-() DELETE r` 1회성 레거시 정리.
- `news/services/news_neo4j_sync.py:700`: 고립 NewsEvent 노드 정리 — Neo4j 단방향.

**시나리오**: Neo4j 측 엣지가 외부 작업/수동 cypher로 삭제되어도 PG `neo4j_dirty=False`이면 영원히 재동기화되지 않음. 반대로 Neo4j에 stale 엣지가 남아 PG에 없는 관계로 보일 수 있음.

> **권장**: 주 1회 reconciliation 태스크 (PG count vs Neo4j count, 샘플 100개 일치 확인).

### 3.4 `RelationConfidence.save()` 자동 dirty=True 부작용 — 🟠 High

`chainsight/models/relation_discovery.py:148-161`:
```python
def save(self, *args, **kwargs):
    ...
    self.neo4j_dirty = True   # ← 항상
    super().save(*args, **kwargs)
```
`save()` 호출 시 무조건 dirty=True로 설정 → **이미 동기화된 레코드를 단순 메타 업데이트해도 다시 sync queue 진입**.
- 정상 동작이면 무의미한 idempotent sync.
- **위험**: bulk_update는 save()를 우회하므로 실제 데이터 변경 시 dirty 미설정 가능 → 라인 159 주석도 이를 경고함.

`chainsight/services/neo4j_sync.py:46`: 동기화 후 `queryset.update()`로 dirty=False 설정 (save() 호출 회피) — 올바른 패턴. 단, 이 패턴이 코드베이스 전체에서 일관 적용된다는 보장은 없음.

---

## 4. UniqueConstraint / update_or_create 현황

### 4.1 unique_together / UniqueConstraint 분포

총 **31개 모델**에서 unique 제약 사용 (마이그레이션 제외):

| 패턴 | 사용처 (대표) |
|------|--------------|
| `unique_together` (튜플) | stocks 가격/재무, news, validation, chainsight, serverless, users, thesis 다수 |
| `UniqueConstraint` (명시적 name) | `portfolio/models.py` 4개 (`unique_card_priority_per_run`, `unique_comment_per_run_stock_metric`, `unique_metric_result_per_run_stock`, `unique_percentile_cache`) |

**🟢 Low**: 같은 도메인(portfolio)에서도 `Wallet/WalletHolding`은 `unique_together`, 분석 결과 테이블들은 `UniqueConstraint`로 혼용. Django 5+ 권장은 `UniqueConstraint`이며 마이그레이션 4건(`metrics/migrations/0006_*`, `validation/migrations/0004_*`)이 `unique_together` 제거 후 재설정한 이력 있음 → 점진적 마이그레이션 진행 중으로 추정.

### 4.2 update_or_create 사용처 (94곳 / 49파일) — 🟠 High

`update_or_create`는 Django 내부적으로:
1. `SELECT ... FOR UPDATE` 없이 GET → 없으면 CREATE, 있으면 UPDATE
2. 동시 호출 시 둘 다 GET 실패 → 둘 다 CREATE 시도 → 한쪽이 IntegrityError(unique 제약) → 재시도 로직 없음

**고위험 호출 (concurrent Celery worker가 같은 키로 동시 호출 가능)**:

| 위치 | 모델 | unique key | 위험 |
|------|------|-----------|------|
| `validation/services/benchmark_calculator.py:238` | `PeerMetricBenchmark` | (symbol, fiscal_year, metric_code, preset_key) | Peer 배치 병렬 실행 시 |
| `validation/services/metric_calculator.py:98` | `CompanyMetricSnapshot` | (symbol, fiscal_year, metric_code) | 동일 종목 여러 metric 병렬 |
| `chainsight/tasks/relation_tasks.py:275/309/344` | `RelationConfidence` | (symbol_a, symbol_b, relation_type) | 여러 source provider 동시 추출 |
| `serverless/services/llm_relation_extractor.py:284` | `LLMExtractedRelation` | 동일 LLM 결과 중복 시 |
| `api_request/stock_service.py:390/417` | `DailyPrice` / `WeeklyPrice` | (stock, date) | 다중 동기화 트리거 시 |
| `chainsight/services/seed_selection.py:411` | `SeedSnapshot` | — | 시드 재계산 시 |

**완화 정책 검색 결과**:
- `select_for_update` 사용처: `sec_pipeline/tasks.py:367` 1곳 (Phase A에서 dirty row lock — 우수 사례)
- 트랜잭션 래핑(`transaction.atomic` + locking): 부분적
- IntegrityError handle 후 retry: `rag_analysis/views.py:167` 1곳

→ **사실상 보호 없음**. 단일 Beat schedule + 단일 worker일 때는 안전하지만, `Q neo4j` queue / 병렬 worker 운용 시 race window 노출.

### 4.3 `update_or_create` 직후 별도 `save()` 호출 패턴

`chainsight/tasks/sync_tasks.py:135-137` 등에서:
```python
profile.neo4j_synced = True
profile.neo4j_synced_at = timezone.now()
profile.save(update_fields=["neo4j_synced", "neo4j_synced_at"])
```
**🟡 Medium 위험**:
- `RelationConfidence.save()`는 항상 `neo4j_dirty=True`로 덮어쓰므로(3.4 절), `save()` 호출이 동기화 직후라면 즉시 다시 dirty가 됨.
- 다행히 `CompanyChainProfile`은 `save()` override가 없어 안전. 그러나 동일 패턴을 다른 모델로 확장 시 위험.

---

## 5. Cross‑Cutting 권장 (감사 결과 요약)

> 본 보고는 read‑only 감사이며 코드 수정/이슈 발행 없음. 후속 조치 시 참고.

1. 🔴 **Neo4j 동기화 플래그 통일**: `synced_to_neo4j` 제거(`RelationConfidence`), 모든 모델 `neo4j_dirty + neo4j_synced_at` 패턴으로 일원화. DECISIONS.md에 명시된 원칙을 코드와 일치시킨다.
2. 🔴 **PG↔Neo4j Reconciliation Job** 신규: 주 1회 카운트 비교 + 샘플 100개 일치 검증.
3. 🟠 **`max_retries=1` 정책 점검**: CLAUDE.md `coding-rules`(max_retries=3, exponential backoff) 적용을 동기화 task 5개에 반영.
4. 🟠 **`update_or_create` race 보호**: 고위험 호출 6곳에 `select_for_update` 또는 `IntegrityError` retry 래퍼 추가.
5. 🟠 **`SupplyChainEvidence.target_company` orphan 자동 재매칭**: post_save 또는 별도 Beat 태스크로 `target_company__isnull=True` evidence 정리.
6. 🟡 **`Thesis` self-FK 사이클 검증**: `clean()` 메서드에 `copied_from` 트레이스 검증.
7. 🟢 **`UniqueConstraint`로 점진 마이그레이션 마무리**: stocks/users/news/serverless 잔여 `unique_together`를 `UniqueConstraint`로 통일.

---

## 부록 A: 감사 명령 로그

```bash
# FK 정책 카운트
Grep on_delete=models\.CASCADE  → 93건 / 31파일
Grep on_delete=models\.SET_NULL → 16건 / 9파일
Grep on_delete=models\.PROTECT  → 6건 / 3파일
Grep on_delete=models\.(RESTRICT|DO_NOTHING|SET_DEFAULT) → 0건

# Neo4j 플래그
Grep neo4j_dirty                → 18 파일 hit
Grep synced_to_neo4j|neo4j_synced → 15 파일 hit (중복 포함)

# Race condition
Grep update_or_create           → 94건 / 49파일
Grep select_for_update          → 1건 (sec_pipeline/tasks.py)
Grep IntegrityError ... retry   → 1건 (rag_analysis/views.py)

# Orphan 정리
Grep cleanup_orphan|delete_orphan → 0건 (PG)
                                    1건 (Neo4j: news_neo4j_sync.py)
```

## 부록 B: 4/26 보고 대비 변경 사항

| 항목 | 4/26 | 5/1 | 변화 |
|------|------|-----|------|
| CASCADE | 93/31 | 93/31 | 동일 |
| SET_NULL | 16/9 | 16/9 | 동일 |
| PROTECT | 0 (보고됨) | 6/3 | **신규 발견** — `portfolio` 4건 + `metrics`/`chainsight` 1건씩 (4/26 보고서가 PROTECT를 0건으로 기록한 것은 누락) |
| update_or_create | ~70 (추정) | 94/49 | 정확 카운트 갱신 |
| Critical 이슈 수 | 3 | 3 | 동일 (Stock 폭발 반경, 플래그 분산, reconciliation 부재) |

→ 코드베이스 변경은 거의 없으며, 본 5/1 감사는 **카운트 정확도와 PROTECT 인지 갱신**이 주요 차이.
