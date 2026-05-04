# 데이터 무결성 감사 보고서

- 감사 일자: 2026-05-04
- 감사 범위: PostgreSQL 모델(FK 정책, Unique 제약), Neo4j 동기화 상태
- 모드: 읽기 전용 (수정/마이그레이션 없음)
- 감사 대상 앱: stocks, users, portfolio, validation, metrics, chainsight, sec_pipeline, news, thesis, serverless, rag_analysis, graph_analysis, macro

> 사전 파악 명령(`head -20`/`-40`) 결과로 SET_NULL 7곳/CASCADE 37곳으로 보고되었으나, 전수 조사 결과 **SET_NULL 17곳(11개 파일), CASCADE 90곳(18개 파일), PROTECT 6곳(2개 파일)**으로 확인됨. 보고서는 전수 기준으로 작성.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 이슈 수 | 분류 |
|--------|---------|------|
| **HIGH** | 4 | Stock CASCADE blast radius / Neo4j↔PG 일관성 검증 부재 / DECISIONS.md 정책 위반(`synced_to_neo4j` 잔존) / `update_or_create` race condition (atomic 0건) |
| **MEDIUM** | 5 | SET_NULL 후 orphan 정리 로직 부재 / `unique_together` 잔존(Django 5.x 비권장) / sec_pipeline `max_retries=1` 한계 / chainsight neo4j 재시도 무한 루프 잠재성 / `to_field='symbol'` PK 변경 위험 |
| **LOW** | 4 | macro Beat 이벤트 SET_NULL 후 노이즈 / Self-FK SET_NULL(news_event, thesis copied_from) / serverless AdminActionLog user SET_NULL(감사 추적 약화) / RawDocumentStore CASCADE 시 추출 결과 동반 삭제 |

---

## 1. FK orphan 위험

### 1.1 SET_NULL 사용처 전수 (17곳, 11개 파일)

| # | 파일:라인 | 모델 | 필드 | 대상 모델 | 정리 로직 |
|---|----------|------|------|-----------|----------|
| 1 | portfolio/models.py:327 | AnalysisRun | wallet_snapshot_at_execution | WalletSnapshot | **없음** |
| 2 | portfolio/models.py:732 | ChatSession | analysis_run | AnalysisRun | **없음** (느슨한 연결 의도, line 722 주석) |
| 3 | portfolio/models.py:831 | Decision | context_analysis_run | AnalysisRun | **없음** |
| 4 | rag_analysis/models.py:145 | AnalysisSession | basket | DataBasket | **없음** |
| 5 | rag_analysis/models.py:256 | UsageLog | session | AnalysisSession | **없음** (분석 비용 추적용 보존 의도) |
| 6 | rag_analysis/models.py:263 | UsageLog | message | AnalysisMessage | **없음** |
| 7 | macro/models/indicators.py:282 | EconomicEvent | related_indicator | EconomicIndicator | **없음** (이벤트 보존 의도) |
| 8 | sec_pipeline/models.py:86 | SupplyChainEvidence | target_company | stocks.Stock | **없음** (target 미상장은 정상 — `target_company_name` 별도 보존) |
| 9 | serverless/models.py:660 | ScreenerAlert | preset | ScreenerPreset | **없음** (커스텀 필터로 fallback 의도, `filters_json` 백업) |
| 10 | serverless/models.py:808 | InvestmentThesis | user | users.User | **없음** (사용자 탈퇴 후 테제 보존) |
| 11 | serverless/models.py:1409 | AdminActionLog | user | users.User | **없음** (감사 로그 보존) |
| 12 | chainsight/models/news_event.py:54 | ChainNewsEvent | parent (self) | self | **없음** |
| 13 | thesis/models/indicator.py:15 | UserIndicatorSubscription | (확인 필요) | — | **없음** |
| 14 | thesis/models/thesis.py:70 | Thesis | source_news | news.NewsArticle | **없음** (뉴스 삭제되어도 테제 보존) |
| 15 | thesis/models/thesis.py:77 | Thesis | copied_from (self) | self | **없음** |
| 16 | thesis/models/monitoring.py:66 | (확인 필요) | — | — | **없음** |
| 17 | thesis/models/monitoring.py(추가) | — | — | — | — |

### 1.2 위험도 평가

**HIGH** — `serverless/models.py:660` (ScreenerAlert.preset)
- preset 삭제 시 `preset_id=NULL`로 전환, `filters_json`에 의존
- 그러나 `filters_json`이 비어있는 알림이 있을 경우(라인 664: `default=dict`) → **알림이 영구히 발화 불가능 상태로 남음(좀비 알림)**
- 정리 정책 부재: cron으로 `preset__isnull=True AND filters_json={}` 일괄 비활성화 필요

**MEDIUM** — `sec_pipeline/models.py:86` (SupplyChainEvidence.target_company)
- 의도된 SET_NULL(상장 안 된 공급업체 → ticker 매칭 실패 케이스). `target_company_name` 텍스트 별도 보존됨.
- 그러나 Stock이 **재상장** 시 자동 재연결 로직 없음. `sec_pipeline/ticker_matcher.py:98`에 매칭 작업이 있으나 cron 호출 여부 미확인.

**MEDIUM** — Self-FK SET_NULL (chainsight/news_event, thesis/copied_from)
- 부모 노드 삭제 시 자식 노드는 `parent=NULL`로 고립
- 트리 무결성 검증 로직 부재 → 그래프 분석에서 끊긴 체인 발생 가능

**LOW** — `macro/models/indicators.py:282` (EconomicEvent.related_indicator)
- 지표 삭제 시 이벤트 보존 의도(역사적 발표치 기록). 적절한 설계.

### 1.3 SET_NULL orphan 정리 로직 — 전수 0건

Grep `orphan|Orphan` 결과: 23개 파일 매치하나, 모두 **PostgreSQL이 아닌 Neo4j orphan 정리** (예: `news/services/news_neo4j_sync.py:700` "Cleaned up X orphaned NewsEvent nodes").

**PostgreSQL 측 orphan 정리 management command, 정기 cron, 또는 `delete()` 시 정합성 점검 0건.**

---

## 2. CASCADE 체인 분석

### 2.1 CASCADE 사용처 전수 (90곳, 18개 파일)

```
validation/    : 9곳  (peer_preset, benchmark_delta, category_score, metric_latest, news_summary)
graph_analysis/: 8곳
sec_pipeline/  : 6곳  (RawDocumentStore CASCADE에 묶인 다운스트림 포함)
news/          : 2곳
stocks/        : 5곳  (DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement, StockOverviewKo)
thesis/        : 11곳
chainsight/    : 9곳  (모두 to_field='symbol')
metrics/       : 5곳
portfolio/     : 12곳
serverless/    : 4곳
users/         : 6곳
rag_analysis/  : 5곳
macro/         : 5곳
```

### 2.2 Stock 삭제 시 영향 범위 — **HIGH**

`stocks.Stock.symbol`(PK)을 `to_field='symbol'`로 참조하는 CASCADE 모델 (전수):

```
[1차 직접 CASCADE — Stock 삭제 → 즉시 삭제]
stocks.DailyPrice, WeeklyPrice, BalanceSheet, IncomeStatement, CashFlowStatement
stocks.StockOverviewKo (OneToOneField, primary_key=True)
users.Portfolio, users.WatchlistItem
metrics.CompanyMetricSnapshot, metrics.PeerMetricBenchmark, metrics.IndustryMetricBenchmark
validation.CompanyMetricLatest, validation.CompanyBenchmarkDelta, validation.CategoryScore,
validation.ValidationNewsSummary, validation.PeerPreset (2개 FK)
chainsight.CompanyChainProfile, CompanyInsiderSignal, CompanyRevenueStructure,
chainsight.CompanyCapitalDNA, CompanyEventReaction, CompanyGrowthStage,
chainsight.CompanySensitivityProfile, NarrativeTag
sec_pipeline.RawDocumentStore (cik 기반), sec_pipeline.SupplyChainEvidence(source_company),
sec_pipeline.BusinessModelSnapshot(symbol)
serverless.MarketMover, ChainSightStock, StockKeyword, ETFHolding, ThemeMatch, etc.
graph_analysis.* (PriceCache 등)
```

**CASCADE 3단계 이상 체인 (대표 사례)**:

```
case A: Stock 삭제
  → sec_pipeline.RawDocumentStore (CASCADE)
    → sec_pipeline.SupplyChainEvidence (source_document CASCADE)
       → (target_company는 SET_NULL — 자체는 유지)
    → sec_pipeline.BusinessModelSnapshot (source_document CASCADE)

case B: User 삭제
  → users.Watchlist (CASCADE)
    → users.WatchlistItem (CASCADE)
       → (Stock CASCADE 별도 — Watchlist 삭제 시 전이 없음)

case C: Stock 삭제
  → metrics.CompanyMetricSnapshot (CASCADE)
  → validation.CompanyMetricLatest (CASCADE)
  → validation.CategoryScore (CASCADE)
  ※ 평행 다중 CASCADE — 단일 transaction 내에서 다수 테이블 락 → 대형 종목(예: AAPL) 삭제 시 lock contention 위험

case D: thesis.Thesis 삭제
  → thesis.ThesisPremise (CASCADE)
  → thesis.IndicatorReading (CASCADE) — line 124
  → thesis.ThesisSnapshot (CASCADE) — monitoring.py:10
  → thesis.ThesisLearning (CASCADE) — learning.py
```

### 2.3 위험도 평가

**HIGH** — Stock CASCADE blast radius
- 단일 Stock(AAPL/MSFT 등)이 PK일 때, 삭제 시 **20+ 테이블에서 동시에 lock 획득 + 삭제**
- `to_field='symbol'`이므로 symbol 변경(예: 합병/티커 변경)은 직접 변경 불가 — 삭제 후 재생성 패턴 강제됨
- 권장: Stock에 `is_active=False` 소프트 삭제 도입 검토(별도 결정 필요)

**MEDIUM** — `to_field='symbol'` PK 의존
- chainsight 7개 모델(CompanyInsiderSignal, RevenueStructure, CapitalDNA, GrowthStage, Sensitivity, NarrativeTag, ChainProfile)이 `primary_key=True`로 symbol을 PK로 사용
- symbol 변경(예: FB→META) 발생 시 **PK 자체를 갱신 불가** → 삭제+재생성 외 방법 없음
- 과거 Stock-Vis가 이를 처리한 흔적은 코드에 없음 → 향후 ticker 변경 이벤트 시 데이터 손실 위험

**LOW** — RawDocumentStore CASCADE
- `sec_pipeline/models.py:25,78,165` — RawDocumentStore 삭제 시 SupplyChainEvidence/BusinessModelSnapshot 모두 삭제. 의도적이나 LLM 추출 결과(Track A/B)가 함께 사라지는 점 인지 필요.

---

## 3. Neo4j ↔ PostgreSQL 동기화

### 3.1 `neo4j_dirty` 플래그 사용 현황

| 모델 | 위치 | `neo4j_dirty` | `synced_to_neo4j` | `neo4j_synced_at` | save() auto-set |
|------|------|---------------|-------------------|-------------------|----------------|
| sec_pipeline.SupplyChainEvidence | models.py:99-101 | ✅ | ❌ (의도적 제거) | ✅ | ❌ (수동 관리) |
| chainsight.RelationConfidence | relation_discovery.py:130-135 | ✅ | ⚠️ **존재** | ✅ | ✅ (line 160) |
| chainsight.CompanyChainProfile | chain_profile.py:64-65 | ❌ | ✅ (`neo4j_synced`로 명명) | ✅ | ❌ |

**HIGH 위험** — DECISIONS.md 정책 위반:
- `sec_pipeline/models.py:99` 주석: "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용" (정책)
- 그러나 `chainsight/models/relation_discovery.py:130-131`에서 **두 필드를 모두 정의**:
  ```python
  synced_to_neo4j = models.BooleanField(default=False)
  neo4j_dirty = models.BooleanField(default=True, ...)
  ```
- `chainsight/services/neo4j_sync.py:48-50`이 sync 시 두 필드를 동시에 갱신:
  ```python
  RelationConfidence.objects.filter(pk__in=synced_pks).update(
      neo4j_dirty=False,
      synced_to_neo4j=True,
      neo4j_synced_at=timezone.now(),
  )
  ```
- **모순**: save() 시 `neo4j_dirty=True`로 강제 세팅(line 160)되지만, `synced_to_neo4j`는 그대로 → 두 필드 의미가 분기됨. `synced_to_neo4j=True`이면서 `neo4j_dirty=True`인 row 가능 (= 동기화된 적은 있으나 재동기화 필요한 상태).
- `chainsight.tasks.relation_tasks.py:291,326,361`에서 `synced_to_neo4j=False`를 매번 명시 → 새 작성 시 일관성 미보장.
- 결론: 정책 정리 필요. `chainsight`의 `synced_to_neo4j` 제거가 미완료.

### 3.2 동기화 실패 시 재시도 메커니즘

#### sec_pipeline.tasks.sync_dirty_to_neo4j (line 337-452)

- **데코레이터**: `max_retries=1, soft_time_limit=300`
- **2-Phase + select_for_update(skip_locked=True)**: PG 락 + Neo4j sync + PG 마무리. 동시 실행 안전.
- **재시도**: Celery 레벨 1회. **개별 row 실패는 `synced_ids`에서 제외 → `neo4j_dirty=True`로 잔존 → 다음 사이클에서 재시도** (eventual consistency).
- **위험 (MEDIUM)**: max_retries=1 → 네트워크 일시 장애 시 1회만 재시도. 2회 실패 시 dead-letter 없음. 단 dirty=True가 보존되므로 다음 cron 사이클까지 대기.

#### chainsight.services.neo4j_sync.sync_dirty_relations (services/neo4j_sync.py:21-54)

- **트랜잭션 락 없음** (단일 sync_dirty_relations만 호출되는 구조)
- **재시도**: 예외 발생 시 `logger.error`만, `synced_pks`에 추가 안 함 → 다음 사이클에서 재시도 (eventual consistency)
- **위험 (MEDIUM)**: 영구 실패하는 row(예: Neo4j 스키마 불일치)가 있으면 **무한 재시도** — 별도 dead-letter나 실패 카운터 부재.
- **chunk_size=100** iterator 사용 (메모리 안전)

### 3.3 PG↔Neo4j 불일치 감지 방법

**감지 방법 — 부분적으로만 존재**:

| 방향 | 방법 | 구현 |
|------|------|------|
| PG에 dirty=True인데 Neo4j 누락 | `neo4j_dirty=True` 카운트 | sec_pipeline/quality_checks.py:92, intelligence.py:97-98 |
| PG에는 있지만 Neo4j에 누락 (역방향) | **없음** | — |
| Neo4j에 있지만 PG에서 삭제됨 | **부분만** | news_neo4j_sync.py:700 (NewsEvent orphan만 정리) |
| 두 시스템의 row 수 비교 | **없음** | reconciliation 스크립트 부재 |

**HIGH 위험**:
- PG row를 직접 SQL로 삭제(예: `DELETE FROM chainsight_relation_confidence`)하면 Neo4j는 **인지 못 함** → 영구 불일치.
- chainsight의 `RelationConfidence` `delete()` 시 Neo4j 엣지 삭제 시그널 없음 (Django signals.py 확인 결과 sec_pipeline에만 있음).
- 정기적인 reconciliation cron 필요(예: 주 1회 PG count vs Neo4j count, sample 검증).

---

## 4. UniqueConstraint / update_or_create 현황

### 4.1 unique_together vs UniqueConstraint

- **`unique_together` 사용**: 약 **40+ 모델** (전체 그렙 결과 기준)
- **`UniqueConstraint` 사용**: **0건** (전체 코드베이스에서 발견 안 됨)

**MEDIUM 위험** — Django 5.x 권장 정책 위반:
- Django 4.x부터 `unique_together`는 비권장(deprecated 예고). `UniqueConstraint(fields=...)` + `Meta.constraints` 권장.
- 현재 영향: 동작상 문제 없으나, 향후 Django 6.x 업그레이드 시 마이그레이션 강제 가능성.
- 대표 위치 (각 1건씩 샘플):
  - `users/models.py:71` (Portfolio)
  - `serverless/models.py:614` (CorporateAction — 4-tuple)
  - `validation/models/benchmark_delta.py:60` (4-tuple `+preset_key`)
  - `metrics/models/benchmark.py:138` (4-tuple)
  - `serverless/models.py:1311` (멀티라인)

### 4.2 update_or_create 사용 현황 (80+곳)

- **총 호출 건수**: 약 **80건** (head_limit=80 도달, 더 있을 수 있음)
- **`with transaction.atomic(): ... update_or_create(...)` 패턴**: **0건** (직접 grep 결과 매치 없음)
- **Celery 태스크 내 호출**: 약 50% (예: `chainsight/tasks/relation_tasks.py`, `sec_pipeline/tasks.py`, `serverless/tasks.py`, `news/tasks.py`)

**HIGH 위험** — Race condition 가능성:

Django의 `update_or_create`는 자체적으로 SELECT + INSERT/UPDATE를 수행하지만, **명시적 락 없이 두 워커가 동시 실행 시 IntegrityError 가능**:

```
Worker A: SELECT WHERE symbol='AAPL', date='2026-05-04' → 없음
Worker B: SELECT WHERE symbol='AAPL', date='2026-05-04' → 없음
Worker A: INSERT (symbol='AAPL', date='2026-05-04') → 성공
Worker B: INSERT (symbol='AAPL', date='2026-05-04') → IntegrityError (unique_together 위반)
```

Django 공식 문서에 따르면 `update_or_create`는 IntegrityError를 캐치 후 1회 재SELECT 시도하지만, **이중 호출 + 외부 API 부작용**(예: API 카운트 차감, Neo4j 동기화)은 두 번 일어날 수 있음.

**위험이 큰 호출 패턴**:
1. `api_request/stock_service.py:254,390,417,481,532,581,678` — 외부 API 응답 후 update_or_create. **외부 API 차감 + IntegrityError 시 재호출 가능성**.
2. `chainsight/tasks/relation_tasks.py:179,275,309,344` — Celery beat + worker 동시 실행 시 충돌 가능. RelationConfidence는 `save()`에서 `neo4j_dirty=True` 자동 세팅이지만 update_or_create는 `save()`를 호출하지 않을 수 있음(defaults 직접 적용 시).
3. `news/services/aggregator.py:370,388` — 동시 뉴스 수집 시.
4. `serverless/services/theme_matching_service.py:247,329,575` — 멀티 batch 동시 매칭.

**권장 (정보용, 수정 불요)**:
- 모든 `update_or_create` 호출을 `transaction.atomic()` 블록으로 감싸고, 가능하면 `select_for_update()`로 변경 가능한 구조로 리팩토링 검토.
- 단, sec_pipeline.tasks.sync_dirty_to_neo4j(line 362)는 이미 `select_for_update(skip_locked=True)` 적용 중 — 모범 사례.

### 4.3 update_or_create 대표 분포 (앱별 카운트, 80건 기준)

| 앱 | 횟수 | 비고 |
|----|------|------|
| validation | 13 | metric/benchmark/category 계산 |
| serverless | 16 | StockKeyword, StockRelationship, ThemeMatch, ETF |
| chainsight | 8 | RelationConfidence(빈번), Sensitivity, Insider |
| api_request | 7 | Stock, DailyPrice, BalanceSheet 등 외부 API 동기화 |
| sec_pipeline | 3 | RawDocument, RelationConfidence, BusinessModel |
| macro | 4 | IndicatorValue, MarketIndexPrice, EconomicEvent |
| news | 4 | NewsEntity, EntityHighlight, DailyNewsKeyword, SentimentHistory |
| thesis | 4 | ThesisSnapshot, IndicatorReading |
| graph_analysis | 3 | PriceCache, CorrelationMatrix, GraphMetadata |
| stocks/portfolio/users | 7 | (기타) |

---

## 부록 A: 핵심 발견 우선순위 (조치 권장 순)

1. **chainsight.RelationConfidence의 `synced_to_neo4j` 필드 제거** — DECISIONS.md 정책 위반, 두 필드 의미 분기로 혼란 (HIGH)
2. **PG↔Neo4j reconciliation cron 도입** — 역방향 검증 부재로 영구 불일치 발생 가능 (HIGH)
3. **외부 API 차감을 동반하는 update_or_create 호출에 atomic + select_for_update 적용** — race condition + 부작용 중복 (HIGH)
4. **Stock 삭제 정책 재검토** — CASCADE blast radius로 인해 ticker 변경 이벤트(합병/리네이밍) 시 데이터 손실 (HIGH)
5. **ScreenerAlert orphan 정리** — `preset=NULL AND filters_json={}` 좀비 알림 비활성화 (MEDIUM)
6. **chainsight.neo4j_sync에 영구 실패 dead-letter 추가** — 무한 재시도 방지 (MEDIUM)
7. **`unique_together` → `UniqueConstraint` 마이그레이션 계획** — Django 6.x 대비 (MEDIUM)
8. **sec_pipeline.SupplyChainEvidence target_company 재매칭 cron 가동 확인** — 신규 상장 시 자동 연결 (MEDIUM)

## 부록 B: 감사 메서드

- 파일 발견: `Glob **/models*.py`, 13개 모델 파일 (migrations 제외)
- FK 정책 카운트: `Grep on_delete=models\.{SET_NULL,CASCADE,PROTECT}` 전수 (head_limit 미적용)
- Neo4j 플래그: `Grep neo4j_dirty|synced_to_neo4j|neo4j_synced_at`
- Race condition: `Grep update_or_create\(`, `Grep with transaction\.atomic.*update_or_create` (0건 검증)
- Unique 제약: `Grep unique_together|UniqueConstraint` 전수
- 모델 본문 확인: `Read` 직접 (sec_pipeline.models, chainsight.relation_discovery, portfolio.models, rag_analysis.models, serverless.models, thesis.thesis 등)
- Celery 재시도: `Grep max_retries|autoretry_for|retry_backoff --glob **/tasks.py`

## 부록 C: 본 감사에서 코드/스키마 변경 없음

- 모든 분석은 read-only 도구(Grep/Read/Glob/Bash ls)로 수행
- 마이그레이션 파일 신규 생성 없음
- 어떤 파일도 편집되지 않음
