# 데이터 무결성 감사 보고서

> **감사 일자**: 2026-06-04
> **감사 범위**: FK orphan 위험 · CASCADE 체인 · Neo4j↔PostgreSQL 동기화 · Unique 제약/race condition
> **감사 방식**: 읽기 전용 정적 분석 (코드 미수정)
> **대상 모델 파일**: 18개 앱/패키지, FK on_delete 정의 총 54곳 (CASCADE 47 / SET_NULL 17)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| 🔴 High | 3 | (1) `Stock` 삭제 시 4단계 CASCADE 대량 연쇄 삭제 (블래스트 반경 18개 앱) · (2) SET_NULL 후 orphan 정리 로직 전무 (17곳 전부) · (3) Neo4j↔PG 양방향 drift 자동 감지 부재 |
| 🟡 Medium | 4 | (4) `update_or_create` race condition (127곳, unique 제약 미보장 케이스) · (5) `news` 앱 `neo4j_synced` 플래그 부재로 매 배치 full-scan · (6) sec_pipeline target_company SET_NULL → 끊긴 evidence 재매칭 의존성 · (7) chain_sight `duplicate_of` 자기참조 SET_NULL 후 dangling 참조 |
| 🟢 Low | 3 | (8) `relation_tasks` max_retries=0 (동기화 1회 실패 시 dirty 영구 잔존 가능) · (9) `FilingProcessLog.symbol`이 FK 아닌 CharField (정합성 미보장) · (10) `UnmatchedCompanyQueue.source_symbol` CharField (Stock FK 아님) |

**총 10개 이슈** (High 3 / Medium 4 / Low 3)

가장 시급한 사항은 **SET_NULL 17곳 전부에 orphan 정리(garbage collection) 로직이 존재하지 않는다**는 점과, **Neo4j와 PG 간 불일치를 능동적으로 탐지하는 메커니즘이 없다**는 점입니다.

---

## FK orphan 위험

### SET_NULL 사용처 전수 (17곳)

지시서에 명시된 3개 파일(sec_pipeline, serverless, rag_analysis) 외에 macro, thesis, chain_sight, portfolio, market_pulse에서도 사용 중입니다. 실제 사용처는 다음과 같습니다.

| # | 파일 | 라인 | 필드 | 부모 → 자식 | orphan 정리 |
|---|------|------|------|------------|------------|
| 1 | `services/sec_pipeline/models.py` | 94 | `target_company` | Stock → SupplyChainEvidence | ❌ 없음 |
| 2 | `services/rag_analysis/models.py` | 132 | `basket` | DataBasket → AnalysisSession | ❌ 없음 |
| 3 | `services/rag_analysis/models.py` | 232 | `session` | AnalysisSession → UsageLog | ❌ 없음 |
| 4 | `services/rag_analysis/models.py` | 239 | `message` | AnalysisMessage → UsageLog | ❌ 없음 |
| 5 | `services/serverless/models.py` | 660 | `preset` | ScreenerPreset → ScreenerAlert | ❌ 없음 |
| 6 | `services/serverless/models.py` | 797 | `user` | User → InvestmentThesis | ❌ 없음 |
| 7 | `services/serverless/models.py` | 1353 | `user` | User → AdminActionLog | ✅ 의도적 보존(감사 로그) |
| 8 | `apps/chain_sight/models/news_event.py` | 69 | `duplicate_of` | self → ChainNewsEvent | ❌ 없음 (자기참조) |
| 9 | `macro/models/indicators.py` | 310 | — | — | ❌ 없음 |
| 10~12 | `thesis/models/{monitoring,indicator,thesis}.py` | 66/15/70,77 | — | — | ❌ 없음 |
| 13 | `apps/market_pulse/models/anomaly.py` | 26 | — | — | ❌ 없음 |
| 14~16 | `apps/portfolio/models.py` | 341/768/870 | — | — | ❌ 없음 |

### 🔴 핵심 위험: SET_NULL 후 orphan 정리 로직 전무

코드베이스 전체에서 **NULL이 된 FK를 주기적으로 정리하거나 재매칭하는 배치/시그널이 단 하나도 존재하지 않습니다.** 결과적으로:

1. **`rag_analysis` 누적 orphan**: `DataBasket` 삭제 시 `AnalysisSession.basket`이 NULL이 되지만, basket이 사라진 세션은 영구히 "맥락 없는 세션"으로 잔존합니다. `UsageLog.session`/`message`도 동일 — 비용 추적 로그가 세션/메시지와 끊긴 채 무한 누적됩니다 (TTL/cleanup 부재).

2. **`serverless.ScreenerAlert`**: `preset`이 NULL이 되면 모델 주석상 "커스텀 필터"로 해석되지만(`filters_json` 사용), **삭제된 프리셋의 알림은 `filters_json`이 비어있어 사실상 동작 불능 상태**가 됩니다. NULL 전환 시 `filters_json` 백필 또는 알림 비활성화 로직이 없습니다.

3. **`sec_pipeline.SupplyChainEvidence.target_company`** (이슈 #6): `Stock` 삭제 시 NULL이 되며, 재매칭은 오직 `signals.py::on_unmatched_resolved`가 `UnmatchedCompanyQueue`를 통해 수동 resolve될 때만 발생합니다. 즉 **삭제로 끊긴 evidence를 자동 재연결하는 경로는 없고**, `target_company_name`(CharField)만 남아 Neo4j에는 dangling 엣지로 남을 수 있습니다.

### 🟡 chain_sight `duplicate_of` 자기참조 (이슈 #7)

`ChainNewsEvent.duplicate_of`가 `self` SET_NULL입니다. 원본 이벤트 삭제 시 중복 이벤트의 `duplicate_of`는 NULL이 되지만 `is_duplicate=True`는 그대로 유지됩니다 → **"중복인데 원본이 없는" 모순 상태**. 정합성을 맞추려면 NULL 전환 시 `is_duplicate=False` 동기화가 필요하나 부재합니다.

**권고**: SET_NULL FK 각각에 대해 (a) NULL 레코드 주기적 cleanup 배치, 또는 (b) NULL 전환 후속 정합화 시그널(`pre_delete`/`post_delete`) 중 하나를 도입. 특히 `UsageLog`는 TTL 기반 아카이빙 우선순위 높음.

---

## CASCADE 체인

### CASCADE 사용처 (47곳, 14개 파일)

지시서 명시 7개 파일 외에 macro, metrics, thesis, chain_sight(10개 모델), portfolio, market_pulse, validation(6개 모델)에서도 광범위하게 사용됩니다.

### 🔴 핵심 위험: `Stock` 삭제 블래스트 반경 (가장 많은 FK 참조)

`Stock`은 코드베이스에서 **가장 많이 참조되는 루트 엔티티**입니다. `Stock` 1건 삭제 시 CASCADE로 연쇄 삭제되는 직접 자식 모델:

**stocks 앱 내부 (CASCADE, to_field="symbol" 사용):**
- `DailyPrice` / `WeeklyPrice` (BasePriceData 상속) — 종목당 수천 행
- `BalanceSheet` / `IncomeStatement` / `CashFlowStatement` (BasicFinancialStatement 상속)
- `StockOverviewKo` (OneToOne, primary_key)
- `EODSignal` / `SignalAccuracy`
- `StockNews`

**타 앱 (stocks.Stock 참조, 대부분 CASCADE):**
- users: `Portfolio`, `WatchlistItem`
- metrics: `CompanyMetricSnapshot`, benchmark 계열
- validation: `PeerPreset`, `CompanyMetricLatest`, `CategorySignal`, `CompanyBenchmarkDelta`, `news_summary`
- chain_sight (10개 모델): `chain_profile`, `narrative_tag`, `news_event`, `sensitivity`, `growth_stage`, `event_reaction`, `capital_dna`, `revenue_structure`, `insider_signal`
- sec_pipeline: `RawDocumentStore`, `SupplyChainEvidence`(source), `BusinessModelSnapshot`
- portfolio: 다수

➡️ **`Stock` 단일 삭제는 18개 앱/패키지에 걸친 수만 행을 즉시 삭제**합니다. 운영 중 잘못된 종목 삭제는 복구 불가능한 대량 손실로 이어질 수 있습니다.

### 3단계 이상 연쇄 삭제 추적

가장 깊은 체인은 **sec_pipeline의 4단계**입니다:

```
Stock (삭제)
 └─CASCADE→ RawDocumentStore (sec_filings)
              ├─CASCADE→ SupplyChainEvidence (source_document)   [3단계]
              │            └─ target_company는 SET_NULL (별도)
              └─CASCADE→ BusinessModelSnapshot (source_document) [3단계]
                           └─CASCADE→ BusinessModelEvidence       [4단계] ✅ 최대 깊이
```

추가로 **rag_analysis 3단계**:
```
User (삭제)
 └─CASCADE→ DataBasket (baskets)
              └─CASCADE→ BasketItem (items)              [3단계]
 └─CASCADE→ AnalysisSession (analysis_sessions)
              └─CASCADE→ AnalysisMessage (messages)      [3단계]
                           └─ UsageLog.message는 SET_NULL (체인 끊김)
```

**serverless 3단계**: `User → ScreenerAlert → ScreenerAlertHistory(747)`.

**위험 평가**: CASCADE 체인 자체는 설계상 의도된 정리 동작으로 보이며 orphan을 만들지 않는 측면에서는 안전합니다. 다만 (a) `Stock`/`User` 삭제 시 트랜잭션 크기가 매우 커 락 경합·타임아웃 위험, (b) 4단계 sec_pipeline 삭제 중 일부가 Neo4j에 동기화된 상태라면 **PG에서는 삭제되지만 Neo4j 엣지는 남는 drift**가 발생합니다(아래 동기화 섹션 참조).

### 🟢 정합성 미보장 CharField (이슈 #9, #10)

- `FilingProcessLog.symbol`은 FK가 아닌 `CharField(max_length=20)` — Stock 삭제 시 로그에 dangling 심볼 문자열 잔존(로그 특성상 의도적일 수 있으나 명시 주석 없음).
- `UnmatchedCompanyQueue.source_symbol`도 CharField — 동일.

---

## Neo4j 동기화

### neo4j_dirty 플래그 현황

`audit P0 #9`(2026-04-29)에서 `synced_to_neo4j`/`neo4j_synced` 불리언을 제거하고 **`neo4j_dirty` (True=동기화 필요) 단일 소스**로 통일한 이력이 코드 주석으로 확인됩니다.

| 모델 | 위치 | dirty 플래그 | 동기화 태스크 |
|------|------|------------|--------------|
| `CompanyChainProfile` | `chain_sight/models/chain_profile.py:84` | `neo4j_dirty`(default=True, db_index) + `neo4j_synced_at` | `chainsight-neo4j-dirty-sync` (max_retries=2) |
| `RelationConfidence` | `chain_sight/models/relation_discovery.py:148` | `neo4j_dirty` + index | `neo4j_sync.py::sync_dirty` |
| `SupplyChainEvidence` | `sec_pipeline/models.py:112` | `neo4j_dirty`(default=True) + `neo4j_synced_at` + index | `sync_dirty_to_neo4j` (max_retries=1) |
| `NewsArticle` | `news/` | ❌ **dirty/synced 플래그 없음** | `news_neo4j_sync.py::sync_batch` |

**잘 설계된 부분**:
- `save()` 오버라이드로 dirty 자동 세팅 (`relation_discovery.py:179`).
- `queryset.update()`/`bulk_update`는 `save()` 미호출이므로 **수동 `neo4j_dirty=True` 토글**을 주석과 함께 명시 (`relation_tasks.py:415-435`, `sec_pipeline/signals.py:53`) — 일관성 양호.
- `sync_dirty_to_neo4j`의 2-Phase + `select_for_update(skip_locked=True)` 패턴은 동시성 안전.

### 🔴 핵심 위험: 양방향 drift 자동 감지 부재 (이슈 #3)

**PG에는 있고 Neo4j에 없는(또는 반대) 불일치를 능동적으로 탐지하는 메커니즘이 존재하지 않습니다.**

1. **PG 삭제 → Neo4j 잔존**: 위 CASCADE 섹션에서 본 대로, `Stock` 삭제로 `SupplyChainEvidence`(CASCADE)나 `CompanyChainProfile`이 PG에서 삭제되어도, 이미 Neo4j에 sync된 노드/엣지를 제거하는 `post_delete` 시그널이나 reconciliation 배치가 없습니다 → **Neo4j에 dangling 노드/엣지 누적**.

2. **`news` 앱의 우회 방식** (이슈 #5): `NewsArticle`에 dirty/synced 플래그가 없어, `sync_batch`가 매번 "최근 30일 + llm_analyzed=True 전체를 조회한 뒤 Neo4j에 이미 존재하는 article_id를 제외"하는 방식으로 동작합니다(`news_neo4j_sync.py:546`). 이는 (a) 매 배치 full-scan 비효율, (b) Neo4j 조회 실패 시 중복 생성 위험, (c) 다른 모델들과 일관성 없는 패턴입니다.

3. **재시도 메커니즘 일관성 부족** (이슈 #8): 동기화 태스크별 `max_retries`가 제각각:
   - `chainsight-neo4j-dirty-sync`: max_retries=2 ✅
   - `sec_pipeline sync_dirty_to_neo4j`: max_retries=1
   - `relation_tasks.py:405` (decay 태스크): **max_retries=0** — 1회 실패 시 재시도 없음.

   다만 `neo4j_dirty=False`로의 전환은 **Neo4j 성공 후에만** 일어나므로(`sync_tasks.py:161-163`, `neo4j_sync.py:50`), 동기화 실패 시 dirty=True가 유지되어 **다음 주기에 재처리되는 self-healing 구조**는 갖춰져 있습니다. 이는 재시도 부재를 부분적으로 보완합니다.

**권고**:
- PG `post_delete` 시 Neo4j 노드/엣지 제거 시그널 추가, 또는 주기적 reconciliation 배치(PG id set ↔ Neo4j id set diff) 도입.
- `NewsArticle`에도 `neo4j_dirty`/`neo4j_synced_at` 도입하여 패턴 통일 + full-scan 제거.
- decay 태스크(max_retries=0)도 self-healing 대상인지 확인 후 dirty 토글 보장.

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황 (정상 설정)

| 모델 | 제약 | 평가 |
|------|------|------|
| `stocks.DailyPrice/WeeklyPrice` | `(stock, date)` | ✅ |
| `stocks.{BalanceSheet,Income,CashFlow}` | `(stock, period_type, fiscal_year, fiscal_quarter)` | ✅ |
| `stocks.EODSignal` | `(stock, signal_date, signal_tag)` | ✅ |
| `users.Portfolio` | `(user, stock)` | ✅ |
| `users.Watchlist` / `WatchlistItem` | `(user, name)` / `(watchlist, stock)` | ✅ |
| `users.UserInterest` | `(user, interest_type, value)` | ✅ |
| `rag_analysis.BasketItem` | `(basket, item_type, reference_id)` | ✅ |
| `metrics.*` (benchmark, snapshot) | `(symbol, fiscal_year, metric_code[, preset_key])` | ✅ |
| `macro.*` | `(indicator, date)` 등 | ✅ |
| `chain_sight.ChainNewsEvent` | `(source, source_id)` | ✅ |
| `sec_pipeline.CompanyAlias` | `(alias, context_sector)` — country 의도적 제외 | ✅ 주석 명확 |
| `portfolio.*` | `models.UniqueConstraint` 4곳 | ✅ |
| `sec_pipeline.RawDocumentStore` | `accession_no` unique | ✅ |

대부분의 핵심 테이블에 적절한 복합 unique 제약이 설정되어 있습니다.

### 🟡 update_or_create race condition (이슈 #4)

코드베이스 전체에서 `update_or_create`/`get_or_create`가 **127곳** 사용됩니다(주로 Celery 태스크의 데이터 동기화).

Django의 `update_or_create`는 **원자적이지 않습니다** — 내부적으로 `get → 없으면 create`이며, **동시 실행 시 unique 제약이 없으면 중복 행이 생성**되거나, 제약이 있으면 `IntegrityError`가 발생합니다.

**위험 케이스 분석**:
- ✅ **대부분 안전**: `metrics`, `stocks`, `validation` 등의 `update_or_create`는 위 테이블의 복합 unique 제약과 lookup 키가 일치하여, 최악의 경우 `IntegrityError`로 실패할 뿐 중복은 방지됩니다.
- ⚠️ **점검 필요**: 동일 종목을 **여러 Celery 워커가 병렬 처리**하는 시나리오(예: nightly 자동화에서 종목별 fan-out). 같은 `(symbol, ...)` 키에 동시 `update_or_create`가 몰리면:
  - unique 제약 있음 → 한쪽 `IntegrityError` → 태스크 재시도로 흡수되면 OK, 미흡수 시 데이터 누락.
  - `sec_pipeline/signals.py:64` `CompanyAlias.get_or_create` — `(alias, context_sector)` unique 있으므로 안전.
- 🔍 **`market_pulse`/`serverless` 계산 태스크**: `sector_flow`, `concentration`, `breadth` 등 calculator의 `update_or_create`는 lookup 키와 unique 제약 일치 여부를 개별 검증 권장(이번 정적 분석 범위 밖).

**권고**:
- 병렬 fan-out 태스크에서 동일 키 경합 가능성이 있는 `update_or_create`는 (a) `select_for_update` 트랜잭션으로 감싸거나, (b) `IntegrityError` 재시도를 명시적으로 처리.
- unique 제약이 **없는** `update_or_create` 호출이 있다면(특히 로그성/집계성 모델) 중복 행 누적 위험 — 제약 추가 검토.

---

## 부록: 검증에 사용한 주요 명령

```bash
# SET_NULL / CASCADE 전수
grep -rn 'on_delete=models.SET_NULL' --include='*.py' . | grep -v migrations   # 17곳
grep -rn 'on_delete=models.CASCADE'  --include='*.py' . | grep -v migrations   # 47곳

# neo4j_dirty 사용 현황
grep -rn 'neo4j_dirty\|synced_to_neo4j' --include='*.py' .

# update_or_create 분포
grep -rn 'update_or_create\|get_or_create' --include='*.py' . | grep -v migrations | grep -v test  # 127곳

# unique 제약
grep -rn 'UniqueConstraint\|unique_together' --include='*.py' . | grep -v migrations
```

> **주의**: 본 보고서는 정적 코드 분석 기반입니다. 실제 운영 DB의 orphan 행 수·Neo4j drift 규모는 별도 데이터 카운트 쿼리로 정량 측정해야 정확합니다. 코드는 수정하지 않았습니다.
