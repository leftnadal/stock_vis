# 데이터 무결성 감사 보고서

생성일: 2026-05-02
대상: `/Users/byeongjinjeong/Desktop/stock_vis` (전체 Django 앱)
방식: 정적 코드 감사 (DB 미접속 / 읽기 전용)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 개수 | 카테고리 |
|--------|------|----------|
| 🔴 High | 4 | Stock CASCADE 폭발 반경 / Neo4j 단방향 동기화 / SET_NULL orphan 정리 부재 / 3가지 동기화 플래그 패턴 혼재 |
| 🟠 Medium | 5 | thesis 3단 CASCADE / chainsight `synced_to_neo4j` + `neo4j_dirty` 이중 필드 / NewsArticle dirty 플래그 미설정 / `update_or_create` race (unique_together 미보호) / sec_pipeline Phase B 부분실패 누적 |
| 🟡 Low | 6 | 기타 SET_NULL 위치 / orphan 통계 미수집 / `to_field='symbol'` PK 의존 / 인덱스 부재 / Neo4j 역방향 정합성 부재 / quality_checks 누적임계값 임의값 |

**전체 발견**: SET_NULL FK 16개(8개 파일), CASCADE FK 80+개(15개 파일), `update_or_create` 70+회 호출(35+개 파일), `select_for_update` 7회 호출(4개 파일), Neo4j 동기화 플래그 3가지 패턴 혼재(`neo4j_dirty`, `synced_to_neo4j`, `neo4j_synced`).

---

## FK orphan 위험

### SET_NULL 사용처 전수 (16개, 8개 파일)

지시서에 7개·3개 파일이라 했으나 실제 grep 결과는 16개·8개 파일이며, 보고서는 실측 기준으로 작성한다.

| # | 파일:라인 | 모델/필드 | 참조 대상 | 비고 |
|---|----------|-----------|----------|------|
| 1 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | `stocks.Stock` | 매칭 실패 시 `target_company_name` raw 텍스트는 보존, FK만 NULL |
| 2 | `serverless/models.py:660` | `ScreenerAlert.preset` | `ScreenerPreset` | 프리셋 삭제 후 `filters_json`은 유지(커스텀 모드 전환 의도) |
| 3 | `serverless/models.py:808` | `InvestmentThesis.user` | `users.User` | 사용자 삭제 후 테제 보존 (분석 가치) |
| 4 | `serverless/models.py:1409` | `AdminActionLog.user` | `users.User` | 감사로그는 user 삭제 후 보존 (의도된 보존) |
| 5 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | `DataBasket` | basket 삭제 후 세션 잔존 |
| 6 | `rag_analysis/models.py:256` | `UsageLog.session` | `AnalysisSession` | 세션 삭제 후 비용 로그 보존 |
| 7 | `rag_analysis/models.py:263` | `UsageLog.message` | `AnalysisMessage` | 메시지 삭제 후 비용 로그 보존 |
| 8 | `thesis/models/thesis.py:70` | `Thesis.parent` | `self` (thesis) | 회고 체인 NULL 허용 |
| 9 | `thesis/models/thesis.py:77` | `Thesis.snapshot` | `ThesisSnapshot` | 스냅샷 삭제 후 thesis 잔존 |
| 10 | `thesis/models/indicator.py:15` | `ThesisIndicator.metric_definition` | `metrics.MetricDefinition` | 메트릭 정의 삭제 시 잔존 (위험: 의미 잃은 reading) |
| 11 | `thesis/models/monitoring.py:66` | (모니터링 FK) | (검토 필요) | 추가 분석 필요 |
| 12 | `macro/models/indicators.py:282` | (지표 관계) | (검토 필요) | 추가 분석 필요 |
| 13 | `chainsight/models/news_event.py:54` | `NewsEvent.parent_event` | `self` | 자기참조 SET_NULL |
| 14 | `portfolio/models.py:327` | (포트폴리오 FK) | (검토 필요) | |
| 15 | `portfolio/models.py:732` | (포트폴리오 FK) | (검토 필요) | |
| 16 | `portfolio/models.py:831` | (포트폴리오 FK) | (검토 필요) | |

### Orphan 정리 로직 — **🔴 부재**

코드베이스 전수 검색 결과:
- `__isnull=True` 필터로 orphan을 **읽는** 코드는 다수 존재:
  - `sec_pipeline/quality_checks.py:68`: `target_company__isnull=False` 매칭률 계산
  - `sec_pipeline/quality_checks.py:143`: orphan 통계 표시
- orphan을 **삭제 / 보존 정책 적용**하는 코드는 **0개**:
  - 정기 청소 Celery 태스크 (e.g. `cleanup_orphan_*`) 없음
  - `signals.py`의 `on_unmatched_resolved` (sec_pipeline/signals.py:21)는 **반대 방향** — orphan을 매칭 시 NULL → FK 복구
- `rag_analysis.UsageLog`: session/message FK가 SET_NULL인데, 사용자 1명이 6개월간 1만 회 호출 후 모든 세션을 삭제하면 1만 row가 NULL 상태로 영구 잔존. 비용 분석에는 유용하나 PII / GDPR 관점에서 완전삭제 정책 필요.

**🔴 권고 (High)**: SET_NULL은 "장기 보존 의도"가 명확한 4건(InvestmentThesis, AdminActionLog, SupplyChainEvidence raw name 보존, UsageLog)을 제외하고는 보존 기간 정책(예: 90일 후 hard delete)을 정의하고 cleanup task를 추가해야 한다. 특히 `ThesisIndicator.metric_definition` SET_NULL은 metric 정의가 사라진 reading이 누적되며 reading은 CASCADE도 SET_NULL도 아니라 `metric_definition_id IS NULL`인 reading이 indicator 화면에서 깨질 위험이 있다(추가 검증 필요).

---

## CASCADE 체인

### CASCADE 사용처 분포 (80+개, 15개 파일)

지시서의 37개·7개 파일 추정과 달리 실측 80+ 회. 가장 큰 폭발 반경은 **`stocks.Stock`**.

### Stock 삭제 시 폭발 반경 — **🔴 High**

**Stock에 직접 CASCADE FK 보유한 모델 (실측 25+개):**

| 앱 | 모델 (파일:라인) |
|----|------------------|
| stocks | `DailyPrice` (133), `WeeklyPrice` (244), `StockOverviewKo` (699 OneToOne PK), `BalanceSheet` (756), `IncomeStatement` (801), `CashFlowStatement` (888) |
| users | `PortfolioStock` (28 to_field=symbol), `WatchlistItem` (198) |
| metrics | `CompanyMetricSnapshot` (snapshot.py:19), `IndustryMetricBenchmark` (benchmark.py:12, 100), `PeerMetricBenchmark` (benchmark.py:63, 107) |
| validation | `MetricLatest` (7), `BenchmarkDelta` (7, 12), `CategoryScore` (20), `NewsSummary` (7), `PeerPreset` (20, 50) |
| chainsight | `Sensitivity`(17), `NarrativeTag`(22), `InsiderSignal`(27), `GrowthStage`(18), `CapitalDNA`(22), `EventReaction`(17), `ChainProfile`(12), `RevenueStructure`(20) — 8개 (모두 `to_field=symbol, primary_key=True` 패턴) |
| sec_pipeline | `SupplyChainEvidence.source_company` (82), `BusinessModelSnapshot.symbol` (161) |
| serverless | (예상 다수, 라인별 확인 필요) |
| graph_analysis | (다수, 모델 5개+) |

**3단 이상 CASCADE 체인 후보 (정적 추적):**

1. **Stock → ChainProfile → (chainsight 보조 모델)** — chainsight/models/chain_profile.py:12 CASCADE → 다른 모델이 ChainProfile FK를 가질 경우(미확인) 3단.
2. **Stock → SupplyChainEvidence → (없음, 종단)** — 2단으로 끝.
3. **User → Watchlist → WatchlistItem → ?** (3단)
   - `users/models.py:171` Watchlist user CASCADE
   - `users/models.py:197` WatchlistItem watchlist CASCADE
   - WatchlistItem에 자식 FK 없으면 3단 종단.
4. **User → Thesis → ThesisIndicator → IndicatorReading → ?** — **🟠 4단 의심** (thesis/models/thesis.py:11, indicator.py:10, indicator.py:124, monitoring.py:10, learning.py:29~102 모두 CASCADE).
   - 사용자 1명 삭제 시 thesis 수십 개 + indicator 수백 개 + reading 수만 개 동시 삭제. 트랜잭션 타임아웃 가능성.
5. **User → ScreenerPreset → ScreenerAlert(SET_NULL)** — 1단 후 SET_NULL 분기.
6. **DataBasket(rag_analysis) → BasketItem(78), Snapshot 등** — rag_analysis/models.py:78 CASCADE, 그 아래 195, 249도 CASCADE → 3단.
7. **portfolio/models.py**: 11개 CASCADE FK 집중 — Wallet → Position → ... 다중 단계 가능 (별도 심층 감사 필요).

**🔴 권고 (High)**: Stock 1건 삭제 시 8개 앱 25+ 테이블의 row가 즉시 삭제됨. 운영 환경에서 절대 직접 `Stock.objects.delete()`를 호출하지 않도록 admin/CLI 가드 필요. Stock의 라이프사이클(상장폐지 등)은 `is_active` soft-delete 패턴으로 전환을 검토. 현재 `chainsight/models/*` 8개가 `primary_key=True` + CASCADE 조합이라 stock 삭제 시 PK 자체가 사라지며, 이 PK를 외부에서 참조하는 코드가 있다면 즉시 깨진다.

### `to_field='symbol'` 의존성 — **🟡 Low**

22개 모델이 `to_field='symbol'`을 사용. `Stock.symbol`이 unique=True라는 가정 위에 있는데, ticker 변경(예: FB→META, GOOG→GOOGL split) 시 `Stock.symbol`을 update하면 모든 자식 row의 FK가 PostgreSQL DEFERRED 제약 안에서 갱신되어야 한다. `RENAME` 의도 여부 확인 필요.

---

## Neo4j 동기화

### 동기화 플래그 3가지 패턴 혼재 — **🔴 High**

**A. `neo4j_dirty` (단일 boolean) 패턴**
- 모델: `sec_pipeline.SupplyChainEvidence`
- 파일: `sec_pipeline/models.py:99-101`, 라인 99에 명시적 주석 — *"synced_to_neo4j 필드 금지 — neo4j_dirty만 사용"*.
- 동기화: `sec_pipeline/tasks.py:337-448` `sync_dirty_to_neo4j` (Phase A: select_for_update + Phase B: Neo4j upsert + Phase C: dirty=False).
- 재시도: `max_retries=1, soft_time_limit=300` (라인 337). 1회 재시도, 5분 타임아웃 — **너무 짧음**.

**B. `neo4j_dirty` + `synced_to_neo4j` (이중 boolean) 패턴**
- 모델: `chainsight.RelationConfidence`
- 파일: `chainsight/models/relation_discovery.py:129-145`
- 동기화: `chainsight/services/neo4j_sync.py:47-51`에서 **3개 필드 동시 업데이트**:
  ```python
  RelationConfidence.objects.filter(pk__in=synced_pks).update(
      neo4j_dirty=False,
      synced_to_neo4j=True,
      neo4j_synced_at=timezone.now(),
  )
  ```
- **🟠 Medium**: sec_pipeline은 `synced_to_neo4j` 금지인데 chainsight에선 동시 사용. 두 필드의 의미가 미묘하게 다르다 (`synced_to_neo4j` = "Neo4j에 한 번 보낸 적 있음" vs `neo4j_dirty` = "다음 sync 대기"). 두 플래그가 동시에 `True/False`로 어긋날 수 있음 (예: 첫 sync 후 PG가 변경되어 dirty=True인데 synced_to_neo4j=True 그대로). decay 로직(`relation_tasks.py:389,396,403`)에서 `update(synced_to_neo4j=False)`만 호출하고 `neo4j_dirty=True`는 안 거는 곳도 존재 → **의미적 불일치**.

**C. `neo4j_synced` 단일 패턴 (역방향)**
- 모델: `chainsight.CompanyChainProfile`
- 파일: `chainsight/models/chain_profile.py:64-65`
- 동기화: `chainsight/tasks/sync_tasks.py:103-137` — `neo4j_synced=False`인 row를 찾아 sync 후 `True`. dirty=True 의미를 `synced=False`로 표현.
- 재시도: 별도 max_retries 명시 없음 (확인 필요).

**D. 플래그 없는 패턴 (Neo4j 직접 조회)**
- 모델: `news.NewsArticle`
- 파일: `news/services/news_neo4j_sync.py:542` 주석: *"neo4j_synced 필드가 없으므로, Neo4j에 이미 존재하는 article_id를 제외합니다."*
- 동기화: 매번 Neo4j round-trip하여 누락 article_id를 산출. 부하가 높음.
- **🟠 Medium**: 기사 수가 늘면 N개 기사에 대해 N번 round-trip 또는 IN 쿼리. 인덱스 의존도 높음.

### 재시도 메커니즘 분석

| 태스크 | max_retries | 타임아웃 | 실패 처리 |
|--------|-------------|----------|----------|
| `sec_pipeline.tasks.sync_dirty_to_neo4j` | 1 | soft 300s | Phase B 개별 row 실패 시 `synced_ids`에 추가하지 않고 다음 배치까지 dirty=True 유지 (의도된 부분 진행) |
| `chainsight.tasks.run_neo4j_dirty_sync` | 2 | default_retry_delay=60 | `sync_dirty_relations` 내부 except로 row별 catch, 영구 실패 row 식별 안 함 |
| `chainsight.tasks.sync_to_neo4j` (CompanyChainProfile) | 미확인 | 미확인 | 별도 검증 필요 |

**🟠 Medium**: sec_pipeline의 Phase B 부분 실패는 `synced_ids` 누락으로 다음 배치에서 자동 재시도되지만, **실패 횟수 카운터가 없다**. 동일 row가 영원히 재시도되며 Neo4j 측 문법 오류로 실패하는 경우 무한 루프. `consecutive_failures` 컬럼 또는 별도 dead-letter queue 필요.

### 불일치 감지 메커니즘 — **🔴 High (없음)**

코드 검색 결과 PG ↔ Neo4j 양방향 정합성을 비교하는 함수 / 태스크 / 명령어:
- **없음**.

존재하는 모니터링:
- `sec_pipeline/quality_checks.py:90-97`: PG에서 `neo4j_dirty=True` row 50건 초과만 알림. → **PG에는 dirty=False지만 Neo4j에 없는 누락**은 감지 못함.
- `sec_pipeline/intelligence.py:97-98`: 단순 카운트 (synced/pending).

**감지 못하는 케이스:**
1. PG → Neo4j: dirty=False인데 Neo4j 노드 없음 (Phase B 성공 후 Neo4j에서 수동 삭제된 경우)
2. Neo4j → PG: Neo4j에 edge가 있는데 PG의 RelationConfidence가 hard-delete된 경우 (orphan edge)
3. 메타데이터 표류: `confidence_grade`가 PG에서 변경됐지만 dirty 플래그가 갱신 안 된 경우 (chainsight `RelationConfidence.save()` 라인 159-160에서 자동 세팅하나 `bulk_update`는 호출 안 됨 — 주석 명시)

**🔴 권고 (High)**: nightly cron으로 양방향 정합성 비교 태스크 추가:
```
1. PG에서 (source, target, type) tuple SET 추출
2. Neo4j에서 동일 SET 추출
3. SET 차집합으로 PG-only / Neo4j-only / 양측 존재하지만 metadata 불일치 분류
4. 임계값 초과 시 알림 (현재 없음)
```

---

## Unique 제약조건

### unique_together / UniqueConstraint 분포

`unique_together` 사용: **27개 (실측)**, 주요 패턴은 시계열 데이터의 `(symbol, date)`.

| 카테고리 | 모델 | 키 |
|----------|------|-----|
| 시계열 가격 | `stocks.DailyPrice`, `WeeklyPrice` | `(stock, date)` |
| 재무제표 | `BalanceSheet`, `IncomeStatement`, `CashFlow` | `(stock, period_type, fiscal_year, fiscal_quarter)` |
| 시그널 | `stocks.SignalAccuracy` | `(stock, signal_date, signal_tag)` |
| 사용자 | `Portfolio`, `Watchlist`, `WatchlistItem`, `UserInterest` | `(user, ...)` |
| EOD/Movers | `serverless.Mover`, `IntradayPrice`, `MarketBreadth` 등 | `(symbol, date)` 또는 `(date, mover_type, symbol)` |
| 그래프 | `graph_analysis.*` | `(watchlist, date)`, `(stock, date)` |
| 메트릭 | `metrics.*`, `validation.*` | `(stock, metric_definition, ...)` |
| 관계 | `serverless.StockRelationship` | `(source_symbol, target_symbol, relationship_type)` |
| 키워드 | `serverless.StockKeyword` | `(symbol, theme_id)` |
| 기관/ETF | `InstitutionalHolding`, `ETFHolding` | `(institution_cik, stock_symbol, report_date)`, `(etf, stock_symbol, snapshot_date)` |
| 별칭 | `sec_pipeline.CompanyAlias` | `(alias, context_sector)` |
| 분석 | `rag_analysis.BasketItem` | `(basket, item_type, reference_id)` |

`UniqueConstraint`(class-based) 사용: 4개, 모두 `portfolio/models.py` (439, 525, 583, 701).

### update_or_create race condition 분석

전수: **70+ 회 호출 (35+ 파일)**. 위험도 분류:

**🟢 Low risk (unique_together 보호 + 단일 라이터)**
- `stocks/services/sp500_eod_service.py:165` DailyPrice — `(stock, date)` unique 보호
- `stocks/services/stock_sync_service.py:171,337` — Stock + DailyPrice
- `serverless/services/sector_heatmap_service.py:106` SectorPerformance — `(date, sector)` unique
- `news/tasks.py:297` SentimentHistory — `(symbol, date)` unique

이 케이스들은 동시 호출 시 PostgreSQL이 `IntegrityError`를 던지고 Django 내부 로직이 retry 없이 재조회하므로 안전.

**🟠 Medium risk (unique_together 보호 + 다중 워커)**
- `validation/services/benchmark_calculator.py:83,238,272,330` — 다중 워커가 동일 `(stock, metric)` 키를 동시 갱신할 경우 마지막 write가 승리. defaults dict의 부분 필드 갱신 시 일부 필드 손실 가능.
- `chainsight/tasks/relation_tasks.py:179,275,309,344` — Celery 워커 N개가 동일 `(symbol_a, symbol_b, type)` 갱신.
- `validation/services/preset_generator.py:118~449` (6회) PeerPreset — 사용자가 여러 탭에서 동시 저장 시 race.
- `serverless/services/regulatory_service.py:480,521` StockRelationship — 다중 소스에서 동일 관계 동시 등록.

이 케이스들은 IntegrityError → 재시도 패턴이 코드 내 명시적이지 않음. Django `update_or_create`는 자체 재시도가 없으며, 동시 INSERT 충돌 시 호출자에게 예외 전파됨.

**🔴 High risk (unique_together 미확인 또는 트랜잭션 외부)**
- `serverless/services/keyword_example.py:188`, `news/services/keyword_extractor.py:350`: `StockKeyword`, `DailyNewsKeyword` — unique_together 명시 확인 필요.
- `serverless/services/theme_matching_service.py:247` ThemeMatch — unique 확인 필요.
- `chainsight/services/seed_selection.py:411` SeedSnapshot — unique 확인 필요.

### `select_for_update` 사용 현황 (방어 패턴)

7회만 사용:
- `sec_pipeline/tasks.py:367` `skip_locked=True` (배치 처리, 이상적 패턴)
- `users/views.py:695,864` Watchlist 갱신 (적절)
- `rag_analysis/views.py:143,252` DataBasket 갱신 (적절)

**🟠 Medium**: `update_or_create` 호출처 70+ 중 select_for_update로 명시 보호된 곳은 **0개**. Django의 update_or_create 내부 atomic + UNIQUE 제약 의존이지만, defaults dict가 다른 트랜잭션에서 읽힌 값에 의존하는 경우 lost update 가능. 특히 `chainsight/tasks/relation_tasks.py`의 동시 worker 갱신 패턴은 정밀 검증 필요.

---

## 부록: 추가 점검 필요 항목

1. **`portfolio/models.py`**: SET_NULL 3건 + CASCADE 11건 + UniqueConstraint 4건 집중 분포. 단독 심층 감사 1세션 필요.
2. **`metrics.MetricDefinition` 변경 영향**: SET_NULL(thesis indicator) + CASCADE(metrics snapshot) 혼재 — 정의 1건 변경/삭제 시 행동이 갈림. 의도성 검증 필요.
3. **`stocks/models.py:888`** `null=True, blank=True` + CASCADE 조합 (라인 888): null FK인데 CASCADE는 의미 없음. SET_NULL이 의도였을 가능성.
4. **Soft-delete 부재**: 전체 코드에서 `is_active=False` 또는 `deleted_at` 패턴 사용처 거의 없음. Hard-delete 일변도. 운영 사고 시 복구 불가.
5. **Neo4j 측 제약**: PG의 unique_together와 동등한 Neo4j unique constraint(Cypher `CREATE CONSTRAINT ... IS UNIQUE`) 설정 여부 미검증.

---

## 결론

| 우선순위 | 권고 |
|---------|------|
| 1 | Stock 삭제 가드 + soft-delete 도입 (CASCADE 폭발 반경 25+ 테이블) |
| 2 | PG ↔ Neo4j 양방향 정합성 nightly cron 추가 (현재 단방향만) |
| 3 | `synced_to_neo4j` + `neo4j_dirty` 이중 필드 패턴 → `neo4j_dirty` 단일 필드로 통합 (sec_pipeline 정책 따라) |
| 4 | SET_NULL orphan 보존 정책 정의 + 정기 청소 task (특히 `rag_analysis.UsageLog`, `thesis.IndicatorReading`) |
| 5 | `update_or_create` 다중 워커 호출처에 `select_for_update` 또는 advisory lock 도입 (validation/benchmark, chainsight/relation) |
| 6 | sec_pipeline Phase B `consecutive_failures` 카운터 추가 (영구 실패 row dead-letter) |
