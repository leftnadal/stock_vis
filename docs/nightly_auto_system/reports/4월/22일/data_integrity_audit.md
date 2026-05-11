# 데이터 무결성 감사 보고서

- **감사일**: 2026-04-22
- **범위**: Django 모델 FK/CASCADE/UniqueConstraint + Neo4j 동기화 + 레이스 컨디션
- **방법**: 읽기 전용 코드 감사 (grep + 모델 파일 정독). 실제 DB 스캔은 수행하지 않음.
- **결론 한 줄**: Stock 삭제 시 연쇄 파급이 큼. `neo4j_dirty` 패턴은 sec_pipeline에서 견고하나 chainsight는 중복 필드 존재. SET_NULL 후 orphan 정리 로직 전무.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 대표 이슈 |
|--------|------|----------|
| 🔴 Critical | 3 | ChainNewsEvent PROTECT로 Stock 삭제 차단 · thesis 4단계 CASCADE · chainsight 동기화 필드 이중화 |
| 🟠 High | 5 | SET_NULL orphan 정리 전무 · update_or_create transaction 미감싸기 · Neo4j → PG 역방향 불일치 감지 없음 · bulk_update 시 neo4j_dirty 미자동설정 경고(코드 내 주석) · User CASCADE 연쇄 파급 |
| 🟡 Medium | 4 | `to_field='symbol'`과 PK 변경 위험 · Watchlist 삭제 시 graph 전체 재계산 필요 · UniqueConstraint 대신 unique_together(legacy) · SECTION 재동기화 크론 부재 |
| 🟢 Low | 2 | duplicate_of self-FK SET_NULL 정상 · macro/tasks.py cleanup_old_data 예시는 있음 |

실제 카운트 보정 (지시서 기준):
- 지시서: SET_NULL **7곳 3개 파일**. **실측 14곳 8개 파일** — 누락된 5개 파일(thesis/models, macro/models, chainsight/models/news_event.py)이 포함되지 않음.
- 지시서: CASCADE **37곳 7개 파일**. **실측 80+곳 15+개 파일** — `*/models/*.py` (서브디렉토리) 포함 시 validation/ 5개, metrics/ 4개, chainsight/ 8개, thesis/ 10개, macro/ 5개 추가.

---

## FK orphan 위험

### 1. SET_NULL 사용처 (14곳, 8개 파일)

| 파일 | 라인 | 필드 | Target | 해석 |
|------|------|------|--------|------|
| sec_pipeline/models.py | 86 | `SupplyChainEvidence.target_company` | stocks.Stock | LLM 추출 회사명이 Ticker 매칭 실패 또는 Stock 삭제 시 NULL. 의도적. |
| serverless/models.py | 660 | `ScreenerAlert.preset` | ScreenerPreset | 프리셋 삭제 시 커스텀 필터로 폴백. 의도적. |
| serverless/models.py | 808 | `InvestmentThesis.user` | users.User | 사용자 삭제 시 테제 보존. 개인정보 관점 **재검토 필요**. |
| serverless/models.py | 1409 | `AdminActionLog.user` | users.User | 감사 로그 보존. 정상. |
| rag_analysis/models.py | 145 | `AnalysisSession.basket` | DataBasket | 바구니 삭제 시 세션 기록 보존. 정상. |
| rag_analysis/models.py | 256, 263 | `UsageLog.session`, `UsageLog.message` | AnalysisSession, AnalysisMessage | 비용 추적 로그 보존. 정상. |
| chainsight/models/news_event.py | 54 | `ChainNewsEvent.duplicate_of` | self | 원본 중복 해제 시 NULL. 정상. |
| thesis/models/thesis.py | 70 | `Thesis.source_news` | news.NewsArticle | 뉴스 삭제 시 가설은 살아있음. 정상. |
| thesis/models/thesis.py | 77 | `Thesis.copied_from` | self (Thesis) | 원본 가설 삭제 시 복사본 보존. 정상. |
| thesis/models/indicator.py | 15 | `ThesisIndicator.premise` | ThesisPremise | 전제 삭제 시 지표는 고아로 유지 (thesis는 여전히 참조). 정상. |
| thesis/models/monitoring.py | 66 | `ThesisAlert.indicator` | ThesisIndicator | 지표 삭제 시 과거 알림 보존. 정상. |
| macro/models/indicators.py | 282 | `EconomicEvent.related_indicator` | EconomicIndicator | 지표 삭제 시 이벤트 자체는 보존. 정상. |

### 2. SET_NULL 후 orphan 정리 로직 — **존재하지 않음**

- 전체 리포지토리에서 `orphan`, `cleanup_set_null`, `purge_null` 등의 키워드 배치 태스크 **0건**.
- 유일하게 `macro/tasks.py:229 cleanup_old_data()`가 있으나, **SET_NULL 결과를 정리하는 게 아니라 365일 이전 데이터 자체를 삭제**하는 TTL 작업.
- 실무 결과:
  - `SupplyChainEvidence.target_company=NULL` 레코드가 시간에 따라 누적 → `quality_checks.py:91`의 "dirty 적체 > 50" 알림은 작동하지만 NULL 자체는 알림 대상이 아님.
  - `InvestmentThesis.user=NULL` → GDPR/개인정보 삭제 요청 시 본문(title/summary)는 남아 개인 투자 판단이 노출될 수 있음. **위험**.
- 권고: `purge_orphan_set_null` Celery Beat 태스크 필요 (주 1회, `null=True` 필드 중 `created_at < 90d` 레코드 선별 삭제 또는 익명화).

### 3. 정리 배치 가능성 평가

| 모델 | 삭제 가능? | 사유 |
|------|-----------|------|
| SupplyChainEvidence target_company NULL | ❌ | UnmatchedCompanyQueue가 나중에 matched되면 signal이 업데이트 (sec_pipeline/signals.py:52). 지우면 복구 불가. |
| UsageLog session NULL | ⭕ | 비용 집계는 user 기준이라 session NULL도 허용. 보존 권고 (감사). |
| InvestmentThesis user NULL | ⚠️ | **익명화 필요**. 삭제보다는 user를 `anonymous` sentinel로 교체. |
| ThesisAlert indicator NULL | ⭕ | 읽음 처리 후 30일 경과하면 purge 가능. |

---

## CASCADE 체인

### 1. Stock 삭제 시 영향 범위 (가장 많은 FK 참조)

**1단계 — Stock 직접 참조 (CASCADE)** 총 **25+ 모델**:

```
stocks.Stock (PK=symbol)
├── stocks/
│   ├── DailyPrice, WeeklyPrice (BasePriceData abstract)
│   ├── BalanceSheet, IncomeStatement, CashFlowStatement (BasicFinancialStatement)
│   ├── StockOverviewKo (OneToOne)
│   ├── EODSignal, SignalAccuracy
│   └── StockNews (null=True, blank=True — soft reference)
├── users/
│   ├── Portfolio (to_field='symbol')
│   └── WatchlistItem (to_field='symbol')
├── sec_pipeline/
│   ├── RawDocumentStore (symbol_id)
│   ├── SupplyChainEvidence.source_company (source_symbol_id)
│   └── BusinessModelSnapshot (symbol_id)
├── chainsight/  (7개)
│   ├── CompanyChainProfile, CompanyRevenueStructure, CompanyCapitalDNA,
│   │   CompanyGrowthStage, CompanyEventReaction, CompanySensitivity,
│   │   CompanyInsiderSignal, CompanyNarrativeTag
│   └── ChainNewsEvent (⚠️ PROTECT — 아래 Critical 참조)
├── validation/
│   ├── CompanyBenchmarkDelta, CategoryScore, CompanyMetricLatest,
│   │   ValidationNewsSummary, PeerPreset, UserPeerPreference
├── metrics/
│   ├── CompanyMetricSnapshot, IndustryMetricBenchmark, PeerMetricBenchmark
├── graph_analysis/
│   ├── CorrelationEdge.stock_a / stock_b, PriceCache
└── serverless/
    └── (다수 — StockKeyword 등은 FK 없이 symbol 문자열만 사용)
```

### 2. 🔴 Critical: ChainNewsEvent PROTECT

- 위치: `chainsight/models/news_event.py:23`
- `on_delete=models.PROTECT` + `to_field='symbol'`
- 영향: S&P500 리밸런싱으로 **편출 종목 Stock 레코드 삭제 시 `IntegrityError` 발생**. 파이프라인 중단.
- 경로: `stocks/services/sp500_service.py`의 `update_or_create` 로직은 `is_active=False`만 설정하므로 현재는 우회 중이나, Admin에서 수동 `.delete()` 호출 시 즉시 재현 가능.
- 권고: `SET_NULL` 또는 `DO_NOTHING`으로 전환. 또는 Stock은 "soft delete" (boolean `is_deleted`) 채택.

### 3. 3단계 이상 연쇄 삭제 체인

| 체인 | 단계 | 트리거 | 영향 크기 |
|------|------|--------|----------|
| **User → Thesis → ThesisIndicator → IndicatorReading** | 4 | `User.delete()` | 사용자당 수천 reading 삭제 (장기 계정) |
| **User → Thesis → ThesisPremise** + **→ ValidityRecord** | 3 | `User.delete()` | 마감된 가설 학습 기록 전부 손실 — `thesis/models/learning.py` |
| **User → Thesis → HypothesisEvent** | 3 | `User.delete()` | Phase 1 이벤트 로그 전부 손실 |
| **Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence** | 4 | `Stock.delete()` | SEC 10-K 추출 결과 전부 삭제 |
| **Stock → RawDocumentStore → SupplyChainEvidence** | 3 | `Stock.delete()` | source_company일 때 발동 (target은 SET_NULL) |
| **Watchlist → CorrelationEdge → CorrelationAnomaly** | 3 | `Watchlist.delete()` | 그래프 전체 재계산 필요 |
| **User → DataBasket → BasketItem** + **→ AnalysisSession → AnalysisMessage → (UsageLog SET_NULL)** | 3~4 | `User.delete()` | RAG 대화 기록 전소멸, UsageLog만 NULL로 생존 |

### 4. 위험 평가

- **User 삭제**는 투자자 프로필의 전체 소실과 동의어. `InvestorDNA` OneToOne CASCADE (`thesis/models/learning.py:102`) 포함 → `accuracy_rate` 등 장기 학습 자산 파기.
- **Stock 삭제 시 트랜잭션 크기**: 평균 10년치 DailyPrice(~2,500행) + 40분기 재무제표(~120행) × 3개 문 + EODSignal(~2,500행) + SignalAccuracy × 14시그널 = 단일 Stock당 최대 70,000+ 행 CASCADE. **DB 락 장기화 위험**.
- **권고**:
  - 고빈도 로그성 테이블(EODSignal, SignalAccuracy, IndicatorReading)은 CASCADE 대신 `DO_NOTHING` + 별도 배치 삭제 패턴 검토.
  - `Stock.delete()`를 Admin에서 호출 금지. `StockSyncService`에서 is_active/delisted 플래그로만 관리.

---

## Neo4j 동기화

### 1. `neo4j_dirty` 플래그 사용 현황

| 앱 | 모델 | 필드 | 패턴 |
|----|------|------|------|
| **sec_pipeline** | `SupplyChainEvidence` | `neo4j_dirty` + `neo4j_synced_at` | 단일 플래그. 깔끔. `models.py:99` 주석 "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용" |
| **chainsight** | `RelationConfidence` | `neo4j_dirty` + `synced_to_neo4j` + `neo4j_synced_at` | **중복 필드 공존** (relation_discovery.py:130-131). `save()`에서 항상 `neo4j_dirty=True` 강제 |
| **chainsight** | `CompanyChainProfile` 등 | `neo4j_synced` (별도) | 0004_companychainprofile_neo4j_synced migration에서 도입. `neo4j_dirty`와는 다른 개념 |

### 2. 🔴 Critical: chainsight의 중복 동기화 필드

- `chainsight/models/relation_discovery.py:130` `synced_to_neo4j = models.BooleanField(default=False)`
- `chainsight/models/relation_discovery.py:131` `neo4j_dirty = models.BooleanField(default=True, db_index=True)`
- 두 필드가 공존. `services/neo4j_sync.py:47-51`에서는 둘 다 업데이트:
  ```
  .update(neo4j_dirty=False, synced_to_neo4j=True, neo4j_synced_at=...)
  ```
- DECISIONS에 "synced_to_neo4j 필드 금지 — neo4j_dirty만 사용"이 선언돼 있으나 chainsight는 위반.
- 위험: `save()` override가 `neo4j_dirty=True`만 강제하고 `synced_to_neo4j`는 그대로 → 두 필드 정합성 깨짐. 읽기 측에서 어느 쪽을 믿어야 하는지 불분명.
- 권고: `synced_to_neo4j` 필드 **삭제** (migration + 역전 금지 로직) + `sync_tasks.py:167`의 `synced_to_neo4j=False` 업데이트 제거.

### 3. 동기화 실패 시 재시도 메커니즘

| 태스크 | max_retries | Lock/동시성 제어 | 평가 |
|--------|------------|----------------|------|
| `sec_pipeline.tasks.sync_dirty_to_neo4j` | 1 | `select_for_update(skip_locked=True)` + `transaction.atomic` + BATCH_SIZE 500 | ✅ 모범 |
| `chainsight.tasks.neo4j_dirty_sync_tasks.run_neo4j_dirty_sync` | 2 | 없음 (`.iterator(chunk_size=100)`만) | ⚠️ 동시 실행 시 같은 RC를 두 worker가 upsert 가능 |
| `chainsight.tasks.sync_tasks.sync_relations_to_neo4j` | 1 | 없음 (`sync_dirty_relations` 위임) | 위와 동일 |

- `sec_pipeline`은 **2-Phase + skip_locked** 패턴으로 안전. 실패한 row는 `neo4j_dirty=True` 상태로 남아 다음 주기에 재시도 자동.
- `chainsight`는 `iterator()`만 사용 → Celery worker 2개가 동시에 같은 Beat를 집어 들 경우 **edge 중복 생성 리스크**. `DELETE + CREATE` 패턴이라 중복 자체는 제거되지만 Neo4j 측 race (동일 edge의 두 번 생성 → 한 번 삭제된 후 남음) 가능.
- 권고: `chainsight-neo4j-dirty-sync`도 `select_for_update(skip_locked=True)` 패턴 적용. 또는 Redis lock (`django-redis`의 `cache.add(key, ...)`) 기반 mutex.

### 4. PG ↔ Neo4j 불일치 감지 방법

| 방향 | 감지 방법 | 상태 |
|------|----------|------|
| **PG에 있고 Neo4j에 없음** | `SupplyChainEvidence.filter(neo4j_dirty=True, target_company__isnull=False)` 카운트 | `quality_checks.py:91` — 50건 초과 시 알림 |
| **Neo4j에 있고 PG에 없음** | **없음** | 🔴 사각지대 |
| PG 내 stale | `neo4j_synced_at < now - 7d` | 구현 안 됨 |
| 관계 타입 불일치 | RELATED_TO 레거시 정리는 1회성 로직 (`sync_tasks.py:158-168`) | 부분적 |

- 현재 구조는 **PG → Neo4j 방향만** 신뢰. Neo4j에 수동/실수로 생성된 edge는 감지 불가.
- 권고:
  - 일일 배치 `verify_neo4j_consistency`: Neo4j에서 `source='sec_10k'` edge 전수 조회 → PG `SupplyChainEvidence` id 매칭 → 고아 edge 삭제.
  - 또는 Neo4j edge에 `pg_id` 필드를 기록해 역추적 가능하게 (현재 `sec_pipeline/tasks.py:417-426` CREATE 쿼리에는 `pg_id` 없음).

### 5. bulk_update 관련 주의사항 (코드 내 경고 반영)

- `chainsight/models/relation_discovery.py:159` 주석: "neo4j_dirty 자동 세팅 (bulk_update에서는 save() 미호출되므로 수동 관리 필요)"
- 실제 전체 리포지토리에서 `bulk_update` 사용처는 별도 감사 필요. 만약 `RelationConfidence.objects.bulk_update(..., fields=['truth_score'])`가 어디에선가 호출되고 있다면 **`neo4j_dirty`가 False로 남아 Neo4j에 동기화되지 않음**.

---

## Unique 제약조건

### 1. `unique_together` / `UniqueConstraint` 현황

- **`UniqueConstraint` (신규 API)**: **0건**. 전체 코드베이스에서 `models.UniqueConstraint` 선언 없음.
- **`unique_together` (legacy)**: **30+ 건**, 15+ 모델 파일.
- Django 5.x는 `UniqueConstraint`를 권장 (부분 인덱스, deferrable 등 고급 기능 지원). 현재는 모두 legacy 패턴.
- 권고: 마이그레이션 기회에 점진 전환. 특히 null 허용 필드가 포함된 unique_together는 Postgres에서 NULL을 distinct로 취급하므로 `UniqueConstraint(... condition=Q(field__isnull=False))` 패턴이 더 정확.

### 2. 대표 unique_together (가장 광범위)

| 모델 | 키 | 안정성 |
|------|-----|-------|
| `DailyPrice`, `WeeklyPrice` | `(stock, date)` | ✅ |
| `BalanceSheet`, `IncomeStatement`, `CashFlowStatement` | `(stock, period_type, fiscal_year, fiscal_quarter)` | ✅ |
| `MarketMover` | `(date, mover_type, symbol)` | ✅ |
| `EODSignal` | `(stock, date)` | ✅ |
| `SignalAccuracy` | `(stock, signal_date, signal_tag)` | ✅ |
| `RelationConfidence` | `(symbol_a, symbol_b, relation_type)` | ⚠️ symbol_a/b 정규화 로직이 `neo4j_sync.py:60-63`에 존재. insert 시점에 정규화가 항상 적용되는지 미검증. |
| `CoMentionEdge`, `PriceCoMovement` | `(symbol_a, symbol_b [, period])` | ⚠️ 위와 동일 |
| `CorrelationEdge` | `(watchlist, stock_a, stock_b, date)` | ⚠️ (stock_a, stock_b) 순서 정규화 필요 여부 확인 |
| `CompanyAlias` | `(alias, context_sector)` | `context_country` 주석으로 "unique key에 포함하지 않음" 명시 — 의도적 |

### 3. 🟠 `update_or_create` race condition 분석

- 전체 프로젝트에서 `update_or_create` 호출 **70+ 곳** (`count` 모드로 확인, 테스트 제외).
- Django 공식: `update_or_create`는 **내부적으로 SELECT → INSERT/UPDATE**로 atomic하지 않음. `unique_together` 충돌 시 IntegrityError 후 재시도하지만 **race 윈도우 존재**.
- 보호 방법: `transaction.atomic()` 블록 + `select_for_update()` 필요.

**감사 결과**:
- ✅ **안전**: `sec_pipeline/tasks.py:120 (doc create)`, `sec_pipeline/validator_track_b.py:80` — 상위 함수가 `transaction.atomic` 적용.
- ⚠️ **미확인/불안정** (transaction 블록 없이 호출):
  - `validation/services/benchmark_calculator.py:83, 238, 272, 330` — 배치 호출이라 동시 실행 드물지만 보장 없음.
  - `serverless/services/theme_matching_service.py:247, 329, 575` — Celery 병렬 worker에서 동시 호출 가능.
  - `serverless/services/news_relation_matcher.py:201`, `supply_chain_service.py:328`, `llm_relation_extractor.py:284` — LLM 병렬 요청 후 기록 시 race 가능.
  - `stocks/services/stock_sync_service.py:171, 337` — S&P500 60개 심볼 병렬 동기화 시 동일 `(stock, date)`에 두 워커가 경합 가능.

**권고**:
- 모든 `update_or_create`를 호출하는 서비스 메서드 입구에 `with transaction.atomic():` 추가 또는 `django-concurrency`로 optimistic lock 적용.
- Celery 레벨에서 같은 키를 두 worker가 처리하지 않도록 Redis lock 패턴 도입 (`sec_pipeline`의 `select_for_update(skip_locked=True)` 참고).

### 4. `PROTECT` / `DO_NOTHING` 사용처

| 파일 | 위치 | 정당성 |
|------|------|--------|
| chainsight/models/news_event.py:23 | `ChainNewsEvent.symbol → Stock` PROTECT | 🔴 **부적절** (S&P 리밸런싱 차단). `SET_NULL` 권장 |
| metrics/models/metric_snapshot.py:11 | `CompanyMetricSnapshot.metric_definition → MetricDefinition` PROTECT | ✅ 정당. 지표 정의는 삭제 금지 대상 (역사적 비교 보존) |

---

## 추가 발견 사항

### A. `to_field='symbol'` 의존 (4곳)

- `users.Portfolio.stock`, `users.WatchlistItem.stock`, `stocks.BasePriceData.stock`, `stocks.BasicFinancialStatement.stock`
- Stock의 PK가 `symbol` 문자열이므로 기술적으로는 `to_field` 없어도 동일. 그러나 명시로 의도는 분명.
- 위험: 만약 Stock PK를 서로게이트(integer id)로 마이그레이션하는 날이 오면 4곳 모두 수정 필요 — 모놀리식 변경.

### B. `FK 없이 symbol 문자열만 사용`하는 모델

- `StockKeyword`, `StockSectorInfo`, `VolatilityBaseline`, `MarketMover` 등 serverless/ 다수.
- 주석: `# FK 없이 symbol로 직접 매핑 (독립적 TTL 관리)` (`serverless/models.py:175`)
- 의도: TTL 7일짜리 키워드는 Stock 삭제와 무관하게 자연 만료. 합리적.
- 부작용: Stock이 존재하지 않는 symbol이 들어가도 DB 레벨 검증 없음. 수집 파이프라인에서의 개별 검증 의존.

### C. `stocks.StockNews`는 `null=True, blank=True` CASCADE

- `stocks/models.py:888` `stock = models.ForeignKey('Stock', on_delete=models.CASCADE, null=True, blank=True)`
- NULL 허용이므로 사실상 soft reference. `symbol` char field도 별도 존재 (`stocks/models.py:889`).
- Stock 삭제 시 해당 뉴스 레코드도 삭제되지만, `symbol` 필드가 이미 존재하므로 NULL 처리가 더 적절할 수 있음.

### D. `chainsight/models/chain_profile.py` 외 7개 프로파일 모델의 Stock CASCADE

- 각 프로파일은 Stock 삭제 시 전부 삭제. 재계산은 `chainsight/tasks/profile_tasks.py` 배치로 복원 가능하지만, **외부 LLM 토큰 비용 재소모** 발생.
- 권고: soft delete + 주기적 `compact` 패턴 검토.

---

## 긴급 조치 권고 (우선순위 순)

1. 🔴 **ChainNewsEvent PROTECT → SET_NULL** 전환 (Stock 삭제 경로 복구).
2. 🔴 **chainsight.RelationConfidence.synced_to_neo4j 필드 제거** 및 동기화 로직 통일.
3. 🟠 **Neo4j 역방향 일관성 배치 추가**: `verify_neo4j_consistency` — Neo4j의 `source='sec_10k'` edge를 PG id로 역추적해 고아 정리.
4. 🟠 **`update_or_create` race 보강**: 최소한 S&P500 동기화 경로(`stocks/services/stock_sync_service.py`)와 LLM 관계 추출 경로(`serverless/services/*`)에 `transaction.atomic` 명시.
5. 🟠 **SET_NULL orphan 주기 정리 배치** 추가 (특히 `InvestmentThesis.user=NULL` 익명화).
6. 🟡 **chainsight-neo4j-dirty-sync에 `select_for_update(skip_locked=True)` 적용** (sec_pipeline 패턴 이식).
7. 🟡 **bulk_update 감사**: `RelationConfidence.objects.bulk_update(...)` 호출처에서 `neo4j_dirty` 수동 세팅 여부 확인.

---

## 참고

- 감사 도구: grep + ripgrep 기반 정적 분석. 실제 DB orphan 스캔은 미수행.
- 제외 범위: `tests/` 디렉토리, `migrations/` (모델 선언만 확인).
- 동시 실행된 다른 감사(성능/보안/API 의존성)와 함께 보관: `docs/nightly_auto_system/reports/4월/22일/`.
