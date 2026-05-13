# 데이터 무결성 감사 보고서

- **감사 일시**: 2026-05-13
- **감사 범위**: Django 모델 FK 정책, CASCADE 체인, Neo4j↔PostgreSQL 동기화, Unique 제약/Race condition
- **방식**: 읽기 전용 정적 분석 (코드 수정 없음)

> ⚠️ 사전 파악 단계의 사용처 카운트(SET_NULL 7곳, CASCADE 37곳)는 **부분 집계**였음. 실제 감사 결과 **SET_NULL 17곳 / CASCADE 100+ 곳**이 확인되어 모두 분석에 포함함.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 개수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 **HIGH** | 3 | (H1) SEC `target_company SET_NULL` 시 Neo4j 좀비 엣지, (H2) Stock CASCADE 체인 3단계+, (H3) `queryset.update()` 후 `neo4j_dirty` 수동 토글 누락 위험 |
| 🟠 **MEDIUM** | 4 | (M1) `update_or_create` PostgreSQL race condition 가능성, (M2) `sync_dirty_relations` 실패 시 재시도 없음, (M3) SET_NULL orphan 정리 cron 부재, (M4) Neo4j↔PG 불일치 감지 메커니즘 없음 |
| 🟡 **LOW** | 3 | (L1) `chainsight.neo4j_dirty_sync` max_retries=2(나머지는 max_retries=1), (L2) `SupplyChainEvidence.target_company` index 단독 (neo4j_dirty 복합 X), (L3) `unique_together` 일부는 `UniqueConstraint`로 마이그레이션 안 됨 |

---

## FK orphan 위험

### SET_NULL 전체 사용처 (17곳, 9개 파일)

| 파일 | 라인 | 필드 | 모델 → 대상 | orphan 정리 로직 |
|------|------|------|--------------|------------------|
| `sec_pipeline/models.py` | 86 | `SupplyChainEvidence.target_company` | → `stocks.Stock` | ❌ 없음 (🔴 H1) |
| `chainsight/models/news_event.py` | 54 | `CompanyNewsEvent.duplicate_of` | → self | ❌ 없음 |
| `marketpulse/models/anomaly.py` | 25 | `*.paired_news` | → `MarketPulseNews` | ❌ 없음 |
| `macro/models/indicators.py` | 310 | `*.related_indicator` | → `EconomicIndicator` | ❌ 없음 |
| `serverless/models.py` | 660 | `*Alert.preset` | → preset | ❌ 없음 (커스텀 필터 분기로 처리) |
| `serverless/models.py` | 808 | `InvestmentThesis.*` | 외부 모델 | ❌ 없음 |
| `serverless/models.py` | 1409 | `*.user` | → `users.User` | ❌ 없음 (이력 보존 의도) |
| `rag_analysis/models.py` | 145 | `AnalysisSession.basket` | → `DataBasket` | ❌ 없음 (분석 이력 보존) |
| `rag_analysis/models.py` | 256 | `UsageLog.session` | → `AnalysisSession` | ❌ 없음 (감사 로그) |
| `rag_analysis/models.py` | 263 | `UsageLog.message` | → `AnalysisMessage` | ❌ 없음 |
| `thesis/models/thesis.py` | 70, 77 | `Thesis.source_thesis`, `Thesis.original` | → self | ❌ 없음 (복제 출처 보존) |
| `thesis/models/indicator.py` | 15 | `ThesisIndicator.premise` | → `ThesisPremise` | ❌ 없음 |
| `thesis/models/monitoring.py` | 66 | `ThesisAlert.indicator` | → `ThesisIndicator` | ❌ 없음 |
| `portfolio/models.py` | 327, 732, 831 | `*.wallet_snapshot_at_execution`, `*.analysis_run`, `*.context_analysis_run` | snapshot/run | ❌ 없음 (이력 보존) |

### 🔴 H1: `SupplyChainEvidence.target_company` SET_NULL → Neo4j 좀비 엣지

**문제**:
- `sec_pipeline/models.py:85-89` → `target_company`가 `SET_NULL`이고 `neo4j_dirty` 플래그는 자동 전환되지 않음
- Stock 삭제 시: `target_company` → NULL, **그러나 `neo4j_dirty=False`로 그대로 남음**
- 결과: PG에는 NULL target evidence가 남고, Neo4j에는 해당 엣지가 **삭제되지 않음**
- `sec_pipeline/tasks.py:365`에서 `filter(neo4j_dirty=True, target_company__isnull=False)`만 동기화 → NULL 상태는 영원히 dirty queue에 진입하지 않음

**증거**:
- `sec_pipeline/signals.py:52`에는 alias 업데이트 시 `neo4j_dirty=True`를 강제하는 시그널이 있음 (역방향 케이스만 처리)
- Stock `pre_delete` 시그널은 발견되지 않음 → orphan은 즉시 좀비

**영향 범위**: `SP500Constituent`에서 inactive로 빠진 종목이 SEC evidence 보유 시 Neo4j와 PG 불일치 발생

### 🟠 M3: SET_NULL orphan 일괄 정리 cron 부재

전체 17개 SET_NULL 사용처에 대해:
- 일정 기간 후 NULL 레코드를 일괄 삭제/아카이브하는 cron이 **0개**
- `chainsight/models/news_event.py:54` (`duplicate_of`)처럼 self-FK SET_NULL은 누적될수록 self-referential cycle 감지가 어려워짐
- `rag_analysis/models.py:256,263` UsageLog는 감사 목적인데도 message/session NULL이면 LLM 비용 회귀 분석이 불가능

---

## CASCADE 체인

### CASCADE 사용처 (100+ 곳, 16개 파일)

#### 직접 Stock 참조 모델 (Stock 삭제 시 CASCADE)

| 모델 | 위치 | 영향 |
|------|------|------|
| `stocks.*` 내부 6개 | `stocks/models.py:133, 244, 699, 756, 801, 888` | DailyPrice, WeeklyPrice, OverviewKO, IncomeStatement, BalanceSheet, EODSignal 등 |
| `users.PortfolioStock` | `users/models.py:28` (to_field='symbol') | 사용자 보유 종목 전체 삭제 |
| `users.WatchlistItem` | `users/models.py:198` | 관심종목 항목 삭제 |
| `validation.*` 5개 | `validation/models/*.py` | benchmark_delta, category_score, metric_latest, news_summary, peer_preset |
| `metrics.MetricSnapshot` | `metrics/models/metric_snapshot.py:19` | 분기 지표 히스토리 |
| `metrics.PeerMetricBenchmark` | `metrics/models/benchmark.py` | Peer 통계 |
| `sec_pipeline.*` 4개 | `sec_pipeline/models.py:25, 82, 161` | RawDocumentStore, SupplyChainEvidence(source), BusinessModelSnapshot |
| `chainsight.*` 7개 | `chainsight/models/*.py` | insider, revenue, capital, event, growth, sensitivity, narrative, chain_profile |
| `graph_analysis.*` 4+ | `graph_analysis/models.py:20, 70, 77, 84, 178, 185, 291, 334` | correlation, watchlist 그래프 |
| `portfolio.*` 12+ | `portfolio/models.py` | wallet, snapshot, analysis_run 전반 |

### 🔴 H2: Stock 삭제 시 3단계+ 연쇄 삭제

**3단계 체인 예시**:

```
Stock (예: AAPL)
  └─ CASCADE → RawDocumentStore (sec_pipeline/models.py:25)
       └─ CASCADE → SupplyChainEvidence (sec_pipeline/models.py:78)
                       └─ ❗ Neo4j 엣지 사라지지 않음 (H1과 동일 이슈)
```

```
User
  └─ CASCADE → Portfolio (users/models.py:27)
       └─ CASCADE → PortfolioStock (users/models.py:28)
  └─ CASCADE → Watchlist (users/models.py:171)
       └─ CASCADE → WatchlistItem (users/models.py:197)
            └─ CASCADE → WatchlistCorrelation (graph_analysis/models.py:20)
                          └─ Neo4j 노드 분리되지 않음
```

```
Stock
  └─ CASCADE → CompanyChainProfile (chainsight/models/chain_profile.py:12)
       └─ ❗ Neo4j :Stock 속성 잔존 (sync_profiles_to_neo4j는 dirty=True만 처리)
```

**핵심 영향 범위 (Stock 삭제 시)**:
- PG: 약 **40+ 테이블에 걸쳐 즉시 CASCADE 삭제** (Stock symbol 1건 → 데이터 수십만 row)
- Neo4j: `:Stock`, `:Theme`, supply-chain 엣지가 **자동 정리되지 않음**
- 캐시: `serverless`, `validation`의 Redis 캐시는 `clear_cache` 시그널 없이 stale 상태 유지

**완화 장치 부재**:
- `Stock.delete()` 오버라이드 없음
- `pre_delete` / `post_delete` 시그널 없음 (sec_pipeline/signals.py는 alias 업데이트만)
- 즉, **운영 중 Stock 직접 삭제는 사실상 금지**된 상태이지만 코드상 가드는 없음

### 🟠 M4: 캐시-DB-Neo4j 불일치 감지 부재

- `validation`, `serverless` 응답은 Redis 캐시 → Stock CASCADE 후 캐시 키 무효화 시그널 없음
- 별도 reconciliation cron(예: PG row count vs Neo4j node count)도 없음

---

## Neo4j 동기화

### `neo4j_dirty` 플래그 사용 현황

#### 1. `sec_pipeline.SupplyChainEvidence`
- 필드: `sec_pipeline/models.py:99-101` (`neo4j_dirty`, `neo4j_synced_at`)
- 인덱스: `models.Index(fields=['neo4j_dirty'])` (단독)
- 동기화 태스크: `sec_pipeline/tasks.py:337` `sync_dirty_to_neo4j` (`max_retries=1`)
- 패턴: `select_for_update(skip_locked=True)` + 2-phase + dynamic Cypher type
- 자동 dirty 토글: `update_or_create` save() 후 자동 (audit P0 #9)

#### 2. `chainsight.RelationConfidence`
- 필드: `chainsight/models/relation_discovery.py:129-130, 158`
- 인덱스: `models.Index(fields=['neo4j_dirty'])`
- 동기화: `chainsight/services/neo4j_sync.py::sync_dirty_relations`
- 태스크: `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` `run_neo4j_dirty_sync` (`max_retries=2, default_retry_delay=60`)
- ⚠️ `bulk_update`는 save() 미호출 → 모델 메서드에서 수동으로 `self.neo4j_dirty = True`

#### 3. `chainsight.CompanyChainProfile`
- 필드: `chainsight/models/chain_profile.py:63-65` (`db_index=True`)
- 동기화: `chainsight/tasks/sync_tasks.py:97` `sync_profiles_to_neo4j` (`max_retries=1`)
- 패턴: `profile.save(update_fields=["neo4j_dirty", "neo4j_synced_at"])`

### 🔴 H3: `queryset.update()` 후 `neo4j_dirty` 수동 토글

**위험 패턴 (확인됨)**:
- `chainsight/tasks/relation_tasks.py:388, 395, 402`: `update(relation_status='stale', neo4j_dirty=True)` ← **명시적으로 처리**
- `chainsight/services/neo4j_sync.py:48-51`: `update(neo4j_dirty=False, neo4j_synced_at=...)` ← 동기화 후 처리

**누락 위험**:
- `chainsight/tasks/sync_tasks.py:169` 레거시 RELATED_TO 정리 시 `update(neo4j_dirty=True)` 처리됨 ✓
- 그러나 **신규 코드 작성자가 `qs.update(field=...)` 호출 시 `neo4j_dirty=True` 토글을 잊을 가능성 상존**
- 보호 메커니즘: `Meta.save()` 오버라이드, post_save 시그널 모두 없음

### 🟠 M2: 동기화 실패 시 재시도 메커니즘

| 태스크 | max_retries | retry_backoff | 실패 처리 |
|--------|-------------|---------------|----------|
| `sec_pipeline.sync_dirty_to_neo4j` | 1 | ❌ | `try/except` per row, 실패 row는 dirty 유지 |
| `chainsight.sync_profiles_to_neo4j` | 1 | ❌ | `try/except` per profile, 실패 시 fail++ 카운트만 |
| `chainsight.sync_relations_to_neo4j` | 1 | ❌ | dirty sync 위임, 실패 시 dirty 유지 |
| `chainsight.run_neo4j_dirty_sync` | 2 | ❌ (default_retry_delay=60) | task-level retry는 있으나 partial failure는 row 단위로만 |
| `chainsight.aggregate_chain_profiles` | 1 | ❌ | per-symbol try/except |

**문제**:
- `max_retries=1`은 실제로 **최초 1회 실행 + 1회 재시도 = 총 2회**
- exponential backoff 없음 (Celery `retry_backoff` 미사용)
- Neo4j 연결 장애가 30초+ 지속되면 1차 재시도도 실패 → next beat까지 stale
- CLAUDE.md의 "Celery 태스크: idempotent, max_retries=3, exponential backoff" 원칙 **위반**

### Neo4j ↔ PostgreSQL 불일치 감지 방법

#### 현재 존재하는 검사
- `sec_pipeline/quality_checks.py:92, 144-146`: `evidences.filter(neo4j_dirty=False).count()` vs `neo4j_dirty=True` 카운트만 비교
- `sec_pipeline/intelligence.py:97-98`: 동일

#### **부재**
- PG row count vs Neo4j node/edge count 비교 cron 없음
- Neo4j에만 있고 PG에는 없는 orphan edge 감지 없음
- Stock 삭제 후 Neo4j 잔존 노드/엣지 정리 절차 없음
- 정합성 보고서(예: `chainsight neo4j healthcheck`) 없음

**권장**: 일일 reconciliation 태스크 — `MATCH (s:Stock) WHERE NOT EXISTS PG record` 형태 + PG `neo4j_dirty=False`이지만 Neo4j 누락 검사.

---

## Unique 제약조건

### 전체 분포 (40+ 곳)

#### `unique_together` 사용 (구식)
- `validation/models/*.py` 5건 (peer_preset, metric_latest, benchmark_delta, category_score)
- `stocks/models.py` 7건 (가격, 재무제표, EOD signal)
- `serverless/models.py` 11건 (movers, etf, theme, institutional)
- `graph_analysis/models.py` 4건
- `marketpulse/models/*.py` 6건
- `macro/models/*.py` 4건
- `thesis/models/*.py` 5건
- `metrics/models/*.py` 3건
- `chainsight/models/relation_discovery.py` 1건 (`alias, context_sector` — sec_pipeline)
- `rag_analysis/models.py` 1건 (`basket, item_type, reference_id`)

#### `UniqueConstraint` 사용 (권장)
- `portfolio/models.py:439, 525, 583, 701` 4건 (named constraints)
- `portfolio/migrations/0001_initial.py`: `unique_percentile_cache`, `unique_card_priority_per_run`, `unique_comment_per_run_stock_metric`, `unique_metric_result_per_run_stock`

### 🟡 L3: `unique_together` → `UniqueConstraint` 마이그레이션 일관성 부재

- Django 4.x 권장: `UniqueConstraint`로 통일 (조건부 unique, deferrable 지원)
- 현재: `portfolio`만 부분 마이그레이션, 나머지는 `unique_together` 유지
- 영향: 향후 조건부 unique(예: `is_active=True`인 row만 unique) 필요 시 마이그레이션 비용

### 🟠 M1: `update_or_create` Race Condition 가능성

**현황** (87개 파일에서 사용 — Grep 카운트):

**안전한 패턴 (확인됨)**:
- `sec_pipeline/tasks.py:362-368`: `with transaction.atomic(): select_for_update(skip_locked=True)` ✓
- `stocks/tasks.py:528`: `with transaction.atomic():` 블록 내 ✓
- 대부분의 `update_or_create` 호출은 unique_together 필드 키로 호출됨 → DB 레벨 UPSERT-like 보호

**위험 패턴**:
- `chainsight/tasks/sync_tasks.py:84`: `CompanyChainProfile.objects.update_or_create(symbol=stock, defaults=defaults)` — `transaction.atomic()` **없음**
- 동시 실행 시나리오: Celery beat가 `aggregate_chain_profiles`를 동시에 두 번 실행 (각각 다른 worker) → 같은 symbol에 대한 update_or_create 충돌
- PostgreSQL 기본 isolation은 `READ COMMITTED`이므로 phantom-write로 인한 `IntegrityError` 가능
- Django `update_or_create`는 내부적으로 try/except IntegrityError를 처리하지만, **save() 시 race로 인한 중복 created 호출**은 막지 못함

**구체적 위험**:
- `validation/services/preset_generator.py`, `validation/services/metric_calculator.py` 등에서 batch loop 내 update_or_create 다수 호출
- LLM 태스크 (`rag_analysis`, `news/services/keyword_extractor.py`)에서 동일 키로 동시 작성 시 unique_together 위반 가능

**완화책 부재**:
- 명시적 `transaction.atomic()` 래핑이 일관되지 않음
- `select_for_update()` 사용은 `sec_pipeline/tasks.py`만

---

## 부록: 권장 후속 조치 (코드 수정은 별도 PR로)

| ID | 액션 | 우선순위 |
|----|------|---------|
| A1 | `Stock.pre_delete` 시그널 추가 → 관련 evidence/profile `neo4j_dirty=True` 토글 + Neo4j 노드 정리 | 🔴 |
| A2 | `sec_pipeline.SupplyChainEvidence` 인덱스에 `(neo4j_dirty, target_company)` 복합 추가 | 🟡 |
| A3 | Neo4j↔PG reconciliation cron (`chainsight-reconcile`) 신설 — 일일 실행 | 🟠 |
| A4 | 모든 neo4j sync 태스크에 `autoretry_for=(Neo4jError, ConnectionError), retry_backoff=True, max_retries=3` 통일 | 🟠 |
| A5 | `update_or_create` 호출 패턴 audit — `transaction.atomic()` 누락 처소 일괄 패치 | 🟠 |
| A6 | SET_NULL orphan 정리 cron — 90일 이상 NULL 상태인 audit 로그 아카이브 | 🟡 |
| A7 | `unique_together` → `UniqueConstraint` 점진적 마이그레이션 (validation/serverless 우선) | 🟡 |

---

## 감사 메타정보

- **분석 도구**: Grep + Read (정적 분석)
- **실제 카운트**:
  - SET_NULL: **17곳 / 9개 파일** (사전 파악 7곳보다 +10 발견)
  - CASCADE: **100+ 곳 / 16개 파일** (사전 파악 37곳보다 +63 발견)
  - `update_or_create`/`get_or_create` 호출 파일: **87개**
  - `unique_together`+`UniqueConstraint` 정의: **40+ 곳**
- **검증 미수행 항목**: DB 실측(`COUNT(*)`), Neo4j 실측, 실제 race 발생 여부 — 정적 분석 범위 밖
