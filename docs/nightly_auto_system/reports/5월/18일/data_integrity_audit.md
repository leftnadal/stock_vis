# 데이터 무결성 감사 보고서

작성일: 2026-05-18
범위: Backend Django ORM 모델 + Neo4j 동기화 경로 (읽기 전용 감사)
스코프 외: 코드 수정 없음. 마이그레이션 미실행. SQL 점검 미수행 (정적 분석만).

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 |
|--------|------|------|
| **P0 (즉시 대응)** | 2 | Neo4j 동기화 retry 빈약(max_retries=1) / PG↔Neo4j 불일치 감지 로직 없음 |
| **P1 (단기 대응)** | 4 | SET_NULL orphan 정리 cron 부재 / Stock CASCADE 블래스트 광범위 / `update_or_create` race condition 잠재 / `is_synced_to_graph` 와 `neo4j_dirty` 동기화 패턴 혼재 |
| **P2 (관찰 권고)** | 5 | 일부 unique 제약 누락 / news_event PROTECT 사용 / 3단계 CASCADE 다수 / `synced_to_neo4j` 잔존 주석 / dirty 적체 경고만 있고 자동 백프레셔 없음 |

집계 베이스:
- `on_delete=SET_NULL`: **17개 사이트, 12+ 파일** (사전 파악 “7곳, 3개 파일”보다 실제 광범위)
- `on_delete=CASCADE`: **~90개 사이트, 20+ 파일** (사전 파악 “37곳, 7개 파일”보다 실제 광범위)
- `unique_together` / `UniqueConstraint`: **70+ 모델**에서 사용 (단, 일부 핵심 모델 누락 가능)

> 주: 사전 파악 grep은 `*.py` 매칭이라 `models/*.py` 분할 패키지(chainsight, thesis, metrics, validation, portfolio, macro, marketpulse)는 별도로 카운트해야 한다. 본 보고서는 그 누락분을 포함했다.

---

## FK Orphan 위험 (SET_NULL)

### SET_NULL 사용처 전수 (17건)

| # | 파일:라인 | 부모(삭제 측) | 자식(NULL 되는 측) | 의미 |
|---|----------|---------------|-------------------|------|
| 1 | `sec_pipeline/models.py:86` | `stocks.Stock` | `SupplyChainEvidence.target_company` | 매칭된 거래상대 Stock 삭제 시 evidence 살아남음 |
| 2 | `serverless/models.py:660` | `ScreenerPreset` | `ScreenerAlert.preset` | 프리셋 삭제 시 알림은 커스텀 필터로 폴백 |
| 3 | `serverless/models.py:808` | `users.User` | `InvestmentThesis.user` | 사용자 탈퇴 시 테제 익명화 |
| 4 | `serverless/models.py:1409` | `users.User` | `AdminActionLog.user` | 감사 로그는 사용자 삭제와 무관하게 보존 (감사 목적 정합) |
| 5 | `chainsight/models/news_event.py:54` | `NewsEvent (self)` | `NewsEvent.parent_event` | 부모 이벤트 삭제 시 자식만 살아남음 |
| 6 | `marketpulse/models/anomaly.py:25` | (해당 부모) | Anomaly 참조 FK | 이상치 기록 보존 |
| 7-9 | `thesis/models/thesis.py:70,77` `thesis/models/indicator.py:15` `thesis/models/monitoring.py:66` | 다수 부모 | 가설/지표/모니터링 메타 FK | 부모 삭제 후 메타만 잔존 가능 |
| 10 | `macro/models/indicators.py:310` | 지표 부모 | 파생 데이터 | 거시 지표 삭제 후 파생만 잔존 |
| 11-13 | `portfolio/models.py:327, 732, 831` | 다수 부모 | 포트폴리오 보조 FK | 보조 참조만 NULL |
| 14-16 | `rag_analysis/models.py:145, 256, 263` | `DataBasket`, `AnalysisSession`, `AnalysisMessage` | `AnalysisSession.basket`, `UsageLog.session`, `UsageLog.message` | 비용 로그(UsageLog) 보존 — 분석 세션 삭제해도 청구 추적 가능 |

### 위험 평가

**의도된 SET_NULL (정상)**:
- `AdminActionLog.user`, `UsageLog.session/message`, `InvestmentThesis.user` → 감사/청구 추적 목적. 사용자/세션 삭제 후에도 로그 보존이 정합.
- `SupplyChainEvidence.target_company` → 미매칭 evidence를 표시하기 위한 NULL 허용 (모델 설계상 의도).

**감사상 risk-flag**:
- **P1**: orphan 정리 cron이 존재하지 않는다.
  - `Grep("orphan|cleanup_null|prune", **/tasks.py)` 결과 — Stock SET_NULL orphan을 주기적으로 정리하거나 모니터링하는 Celery 태스크는 발견되지 않았다. (참고: `sec_pipeline/quality_checks.py:144`는 dirty 카운트만 측정.)
  - 결과: NULL FK가 누적되면 Admin UI/통계에서 “unmatched” 비율이 단조 증가만 한다. 운영자가 수동으로 NULL row를 분류·archive하지 않으면 통계 신호가 점차 의미를 잃는다.
  - 권고: `SupplyChainEvidence.objects.filter(target_company__isnull=True, extracted_at__lt=now()-90d)` 정리 또는 `archived_at` 컬럼 추가.

- **P2**: `NewsEvent.parent_event = SET_NULL` (self FK) — 부모 이벤트 삭제 후 자식 체인이 부모 ID = NULL인 채 끊어진다. UI에서 “계보”를 재구성할 때 깨질 수 있음. 다행히 NewsEvent 자체가 PROTECT(`stocks.Stock` 참조)로 보호되어 Stock 삭제로는 전파되지 않는다.

---

## CASCADE 체인

### CASCADE의 “블래스트 광폭” 모델: `stocks.Stock`

**Stock을 직접 가리키는 ForeignKey (정적 grep, ~30개 모델)**:

| 앱 | 모델 (예시) | 위험 |
|----|------------|------|
| stocks | DailyPrice, WeeklyPrice, Income/Balance/CashFlow, KoreanOverview, StockNews, FundFlow, EodSignal | 가격/재무 데이터 전체 동반 삭제 |
| users | Portfolio, WatchlistItem | 사용자 보유/관심 종목 삭제 |
| portfolio | (12+개 FK CASCADE) | 거래·룰·리밸런싱 전체 |
| validation | BenchmarkDelta, CategoryScore, MetricLatest, NewsSummary, PeerPreset, UserPeerPreference | 검증 캐시·사용자 프리셋 |
| chainsight | InsiderSignal, RevenueStructure, CapitalDNA, EventReaction, GrowthStage, Sensitivity, NarrativeTag, CompanyChainProfile | Chain Sight DNA 전체 |
| sec_pipeline | RawDocumentStore.target, SupplyChainEvidence.source_company, BusinessModelSnapshot.symbol | 10-K 파이프라인 evidence |
| metrics | MetricSnapshot, BenchmarkAggregate, UserBenchmarkOverride | 지표 캐시 |
| graph_analysis | (4개 unique-가진 모델) | 상관관계 그래프 |
| serverless | MarketMovers, CorporateAction, ETFHolding, ThemeMatch, InstitutionalHolding 등 | 마켓 무버 / 테마 매칭 |

**의미**: 단일 `Stock` 삭제 = **~30개 테이블의 cascade**. 만약 운영 중 “심볼 정상화”를 한답시고 `Stock.delete()`를 호출하면 전체 사용자 watchlist/portfolio/테제/검증 캐시가 한 번에 증발한다.

**현재 안전장치**:
- `Stock`은 `to_field='symbol'` (PK 아닌 unique 컬럼)을 FK 키로 사용 — `Stock.delete()`가 아닌 “심볼 변경 후 재생성” 패턴을 쓰면 cascade 회피 가능.
- DB 레벨 PROTECT 가드는 **없음**. `chainsight/models/news_event.py:23`만 유일하게 `PROTECT` 사용.
- 권고: `Stock.delete()`는 운영 정책상 금지하고, soft-delete (`is_active=False`) 또는 `archived_at` 컬럼을 도입할 것을 검토. 또는 최소한 `stocks/views.py`에서 DELETE 메서드를 차단.

### 3단계 이상 CASCADE 체인

확인된 깊은 체인 (3-hop):

```
User
 ├─CASCADE→ Watchlist
 │           └─CASCADE→ WatchlistItem
 │                       └─CASCADE→ (Stock via to_field, 단 Stock 쪽 CASCADE는 자식 방향)
 ├─CASCADE→ Portfolio
 │           └─CASCADE→ portfolio.* (12+ 자식)
 └─CASCADE→ analysis_sessions (rag_analysis)
              ├─CASCADE→ AnalysisMessage
              │           └─SET_NULL← UsageLog.message (NULL 처리, 보존)
              └─SET_NULL← UsageLog.session (NULL 처리, 보존)
```

```
Stock
 ├─CASCADE→ SupplyChainEvidence.source_company
 │           └─CASCADE→ source_document(RawDocumentStore)→ ... (역방향이라 영향 X)
 ├─CASCADE→ BusinessModelSnapshot
 ├─CASCADE→ CompanyChainProfile (chainsight)
 │           └─Neo4j sync 영향 (PG 삭제 후 Neo4j에 노드는 남음)
 └─CASCADE→ MetricSnapshot, BenchmarkAggregate
              └─CASCADE→ (다음 단계는 없음, leaf)
```

```
AnalysisRun (portfolio)
 └─CASCADE→ MetricResult
              └─UniqueConstraint(analysis_run, stock, metric_id)
                 + save()시 is_finalized=True면 ValidationError로 차단 (P0 #X 방어)
```

**위험 평가**:
- **P2**: 3-hop CASCADE 자체는 Django ORM이 단일 트랜잭션으로 처리. SQL 락 경합과 시간 비용만 우려.
- **P1**: Stock → CompanyChainProfile / SupplyChainEvidence CASCADE 시, **Neo4j 쪽 잔존 노드가 정리되지 않는다** (아래 “Neo4j 동기화” 섹션 참조). pre_delete signal 미설치.

---

## Neo4j 동기화

### neo4j_dirty 플래그 사용 현황

```
[PG 모델]                              [관리하는 task]
chainsight.CompanyChainProfile        chainsight.tasks.sync_tasks.sync_profiles_to_neo4j
chainsight.RelationConfidence         chainsight.services.neo4j_sync.sync_dirty_relations
sec_pipeline.SupplyChainEvidence      sec_pipeline.tasks.sync_dirty_to_neo4j
```

**설계 원칙 (CLAUDE.md / common-bugs #21 / audit P0 #9 주석)**:
- `neo4j_dirty=True` = “Neo4j 반영 필요” (의미 반전, `synced_to_neo4j`는 폐기됨)
- `update_or_create()`는 `save()`를 호출 → `neo4j_dirty=True`가 자동 세팅됨 (defaults에 명시 X)
- `queryset.update()`는 `save()` 미호출 → **수동으로 `neo4j_dirty=True` 토글 필요** (`chainsight/tasks/relation_tasks.py:388, 395, 402`)
- 동기화 완료 후 PG 업데이트는 반드시 `queryset.update()` 사용 (save() 시 dirty=True 다시 덮어쓰기 방지) (`chainsight/services/neo4j_sync.py:47-51`, `sec_pipeline/tasks.py:441-445`)

### 동기화 실패 시 재시도 (위험: P0)

```
chainsight.tasks.neo4j_dirty_sync_tasks.run_neo4j_dirty_sync — max_retries=2, retry_delay=60s
chainsight.tasks.sync_tasks.sync_profiles_to_neo4j         — max_retries=1, soft_time_limit=1800
chainsight.tasks.sync_tasks.sync_relations_to_neo4j        — max_retries=1
sec_pipeline.tasks.sync_dirty_to_neo4j                     — max_retries=1
```

**문제**:
- `max_retries=1` 또는 2. exponential backoff 없음.
- **개별 row 단위 try/except가 있어 에러 발생 row는 “synced_pks”에서 빠지고 dirty=True로 영구 잔존**. 다음 sync에서 자동 재시도되긴 함 — 즉 영원히 실패하는 row가 매 sync마다 비용을 발생.
- 영원 실패 row 격리/격리큐 없음. `sec_pipeline.SupplyChainEvidence`에 `sync_attempts` / `last_sync_error` 컬럼 없음.

**감지 메커니즘 (있음)**:
- `sec_pipeline/quality_checks.py:90-97`: dirty 적체가 50건 초과면 alerts list에 메시지 추가.
- `sec_pipeline/intelligence.py:97-98`: 대시보드 stats에 sync_pending 카운트 노출.
- 자동화된 운영자 호출(Slack/Email)이나 백프레셔(생성 일시정지) 로직은 **없음**.

### PG ↔ Neo4j 불일치 감지 (위험: P0)

**현재 상태**: PG와 Neo4j 사이 정합성 검증(reconciliation) 로직이 **없다**.

확인한 흐름:
- PG → Neo4j: `neo4j_dirty=True` 플래그 기반 push만 존재.
- Neo4j → PG: 역방향 검증 없음.
- Stock CASCADE 삭제 시 Neo4j 노드 cleanup: **pre_delete signal 미존재**. 즉 PG에서 Stock이 삭제돼도 Neo4j `(Stock {ticker:...})` 노드는 그대로 남는다.
- `RelationConfidence`가 deleted 됐을 때 Neo4j edge 정리: `neo4j_sync.py:77 _delete_edge`가 있긴 하나, 이는 `relation_status in ('hidden','weak','stale')`일 때만 호출. **PG row delete 자체에 대한 hook이 없다**.

권고 (감사 의견만; 코드 수정 금지):
1. **P0**: 주기적 reconciliation job 신설.
   - PG의 `Stock` symbol set ↔ Neo4j `MATCH (s:Stock) RETURN s.ticker`. diff 출력.
   - PG `RelationConfidence` count ↔ Neo4j edge count. relation_type별 비교.
2. **P0**: `Stock.delete()` 호출에 대해 `pre_delete` signal로 Neo4j 노드 cleanup 또는 “delete 금지” 가드 추가.
3. **P1**: dirty가 N회 sync에서 연속 실패한 row를 quarantine 테이블로 이동.

### `is_synced_to_graph` vs `neo4j_dirty` 혼재 (위험: P1)

```
serverless/models.py:1319   index=is_synced_to_graph
serverless/services/supply_chain_service.py:119  neo4j_synced = self._sync_to_neo4j(...)
news/api/views.py:1989      "NewsArticle에 neo4j_synced 전용 필드 없음" (주석)
news/services/news_neo4j_sync.py:542  "Neo4j에 이미 존재하는 article_id를 제외"
```

- `LLMExtractedRelation`(serverless)는 `is_synced_to_graph` 컬럼을 갖는 반면, chainsight/sec_pipeline는 `neo4j_dirty`(반대 의미)를 쓴다. **두 패턴이 한 코드베이스에 공존**한다.
- 신규 코드를 작성할 때 어떤 패턴을 따라야 할지 혼란. DECISIONS.md에 “neo4j_dirty 단일 소스” 결정이 있으나, `serverless/`와 `news/`가 마이그레이션되지 않았다.

---

## Unique 제약조건

### 핵심 unique 제약 (가격/재무/시계열)

| 모델 | 키 | 목적 |
|------|----|------|
| `stocks.DailyPrice` | (stock, date) | 일별 OHLCV idempotent |
| `stocks.WeeklyPrice` | (stock, date) | 주별 |
| `stocks.IncomeStatement/BalanceSheet/CashFlow` | (stock, period_type, fiscal_year, fiscal_quarter) | 재무제표 |
| `stocks.EodSignal` | (stock, signal_date, signal_tag) | EOD 14개 시그널 |
| `serverless.MarketMovers` | (date, mover_type, symbol) | 마켓 무버 |
| `serverless.CorporateAction` | (symbol, date, action_type) | 액션 dedupe |
| `serverless.LLMExtractedRelation` | (source_symbol, target_symbol, relation_type, source_id) | LLM 추출 결과 |
| `chainsight.RelationConfidence` | (symbol_a, symbol_b, relation_type) | 관계 dedupe |
| `chainsight.RelationCandidate` | (symbol_a, symbol_b, period) | 후보 dedupe |
| `chainsight.NewsEvent` | (source, source_id) | 외부 ID dedupe |
| `validation.MetricLatest` | (symbol, metric_code) | 최신 지표 |
| `validation.BenchmarkDelta` | (symbol, fiscal_year, metric_code, preset_key) | preset별 델타 |
| `metrics.MetricSnapshot` | (symbol, fiscal_year, metric_code) | 지표 스냅샷 |
| `news.NewsKeyword` | (symbol, date) (추정) | 키워드 dedupe |
| `users.Portfolio` | (user, stock) | 포트폴리오 |
| `users.Watchlist` | (user, name) | watchlist |
| `users.WatchlistItem` | (watchlist, stock) | watchlist item |

총 **70+개 모델**에 unique 제약 존재. 핵심 시계열은 잘 보호됨.

### 누락 의심 (위험: P2)

- `chainsight.CompanyChainProfile` — Grep에서 unique 제약 미발견. Stock과 1:1이라면 OneToOne으로 선언해야 하나, ForeignKey만 있을 가능성. (모델 추가 정독 필요. 단, save 로직에서 id로 update_or_create 한다면 race condition은 적음.)
- `sec_pipeline.BusinessModelSnapshot` — (symbol, as_of_date) unique 없음. 같은 filing date에 두 번 추출되면 중복 row가 생긴다.
  - 위치: `sec_pipeline/models.py:184-191` — `indexes`만 있고 `unique_together` 없음.
- `sec_pipeline.SupplyChainEvidence` — natural key가 (source_document, source_company, target_company_name, relationship_type) 수준일 텐데 unique 제약 없음. 재처리 시 중복 evidence 생성 가능.

### update_or_create 사용 패턴 (위험: P1)

총 90건 사용 (50 파일). 대다수가 unique 제약과 짝지어 동작 → idempotent.

**race condition 잠재 지점**:

| 위치 | 패턴 | 위험 |
|------|------|------|
| `sec_pipeline/tasks.py:314` | `RelationConfidence.objects.update_or_create(symbol_a, symbol_b, relation_type, defaults={...})` | unique_together와 일치 → 안전. 그러나 동일 Celery worker 풀에서 동일 키로 동시 호출되면 IntegrityError 가능. autoretry 없음. |
| `chainsight/tasks/relation_tasks.py:291` | RelationConfidence update_or_create | 위와 동일 |
| `serverless/services/supply_chain_service.py:1` 외 | 다수 | natural key 매핑 필요 |

Django의 `update_or_create`는 “SELECT → UPDATE or INSERT” 패턴으로 두 트랜잭션이 동시에 들어오면 IntegrityError 발생 가능. unique_together가 있어 DB가 보호하긴 하나, **상위 task에서 IntegrityError를 catch+retry하는 코드는 발견되지 않음** (Celery autoretry_for 미설정).

권고:
- 핵심 sync 태스크에 `autoretry_for=(IntegrityError,)` 추가 검토.
- 또는 락(`select_for_update`) 활용 — `sec_pipeline/tasks.py:367`는 이미 `select_for_update(skip_locked=True)`를 쓰고 있어 좋은 선례.

---

## 결론 / 다음 단계 권고

**즉시 (P0)**:
1. PG ↔ Neo4j reconciliation job 신설 (일 1회).
2. Neo4j sync 태스크 max_retries 상향 + exponential backoff.
3. `Stock.delete()` API 가드.

**단기 (P1)**:
4. SET_NULL orphan 정리 cron (90일 경과 + target_company IS NULL 등).
5. `is_synced_to_graph` 잔존 코드(serverless)를 `neo4j_dirty` 패턴으로 통일.
6. 핵심 update_or_create 태스크에 IntegrityError autoretry.

**관찰 (P2)**:
7. `BusinessModelSnapshot`, `SupplyChainEvidence` natural key unique 제약 추가 검토.
8. dirty 적체 자동 백프레셔(생성 일시정지) 도입 검토.

---

부록: 사전 파악과 실제 grep 결과 차이

| 항목 | 사전 파악 | 실제 (분할 패키지 포함) |
|------|----------|------------------------|
| SET_NULL 사이트 | 7곳 / 3파일 | **17곳 / 12+파일** |
| CASCADE 사이트 | 37곳 / 7파일 | **~90곳 / 20+파일** |
| Stock FK 참조 | (미명시) | **111곳 (전체 grep)** |

사전 grep이 `*.py` 단일 패턴이라 `chainsight/models/*.py`, `thesis/models/*.py`, `metrics/models/*.py`, `validation/models/*.py`, `portfolio/models/*.py`, `macro/models/*.py`, `marketpulse/models/*.py` 등 **모델 분할 패키지**를 잡지 못함. 본 보고서는 `**/models*.py` 글로브로 재집계.
