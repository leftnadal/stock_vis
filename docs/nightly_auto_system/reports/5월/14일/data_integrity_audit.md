# 데이터 무결성 감사 보고서

- **감사일**: 2026-05-14
- **범위**: Django 모델 전체 (Stock-Vis 백엔드)
- **모드**: 읽기 전용 (코드 수정 없음)
- **검색 기준**: `*.py` glob (Django 모델, services, tasks, signals)

---

## 요약 (위험도별 이슈 수)

| 위험도 | 이슈 수 | 카테고리 |
|--------|---------|----------|
| **P0 (Critical)** | 2 | FK orphan cleanup 부재, neo4j PG↔Neo4j 일관성 검증 메커니즘 부재 |
| **P1 (High)** | 4 | Stock CASCADE 광범위, update_or_create race (atomic 없음 ~50건), SET_NULL FK index 부재, rematch_unmatched 명령어의 invalid status 값 |
| **P2 (Medium)** | 3 | save() 부수효과로 neo4j_dirty=True 무조건 세팅, bulk_update 시 neo4j_dirty 미세팅 책임 분산, CompanyAlias context_country unique 제외 의도성 |
| **P3 (Low)** | 3 | Stock.favorite_stock M:N null 처리, AdminActionLog/log 모델 unique 미설정 (의도적), `not_company` ↔ `not_public` 상태 코드 불일치 |

총 **12건** (사전 파악 명령서의 "SET_NULL 7곳, CASCADE 37곳" 값은 실제 코드량(SET_NULL 16곳, CASCADE 90+곳)의 부분 집합으로 보임 — 본 보고서는 실측치 기준).

---

## FK orphan 위험

### 1.1 SET_NULL 사용처 — 실측 16곳 (10개 파일)

| # | 파일:라인 | FK | 대상 모델 | 의도 |
|---|----------|----|---------|------|
| 1 | marketpulse/models/anomaly.py:25 | `(self?)` | (anomaly 기준) | 기준 변경 시 anomaly 보존 |
| 2 | serverless/models.py:660 | `ScreenerAlert.preset` | ScreenerPreset | 프리셋 삭제 시 알림은 커스텀 필터로 유지 |
| 3 | serverless/models.py:808 | `InvestmentThesis.user` | users.User | 탈퇴 후에도 테제 보존 |
| 4 | serverless/models.py:1409 | `AdminActionLog.user` | users.User | 감사 로그 보존 |
| 5 | rag_analysis/models.py:145 | `AnalysisSession.basket` | DataBasket | 바구니 삭제 후 세션 기록 보존 |
| 6 | rag_analysis/models.py:256 | `UsageLog.session` | AnalysisSession | 비용 추적 보존 |
| 7 | rag_analysis/models.py:263 | `UsageLog.message` | AnalysisMessage | 비용 추적 보존 |
| 8 | **sec_pipeline/models.py:86** | **`SupplyChainEvidence.target_company`** | **stocks.Stock** | **Ticker 미매칭 케이스 + 미상장 회사** |
| 9 | portfolio/models.py:327 | `AnalysisRun.wallet_snapshot_at_execution` | WalletSnapshot | 스냅샷 삭제 시 분석 보존 |
| 10 | portfolio/models.py:732 | `ChatSession.analysis_run` | AnalysisRun | 분석 삭제 후 대화 보존 |
| 11 | portfolio/models.py:831 | `Decision.context_analysis_run` | AnalysisRun | 의사결정 영구 보존 |
| 12 | macro/models/indicators.py:298 | (macro 관계) | — | — |
| 13-14 | thesis/models/thesis.py:70, 77 | `source_news`, `copied_from` | NewsArticle, Thesis(self) | 출처 보존성 |
| 15 | thesis/models/indicator.py:15 | (indicator universe) | — | — |
| 16 | thesis/models/monitoring.py:66 | (monitoring) | — | — |
| 17 | chainsight/models/news_event.py:54 | `ChainNewsEvent.duplicate_of` | self | self-FK |

> 사전 파악에서 언급한 "7곳, 3개 파일"보다 광범위함. **모든 SET_NULL 후 orphan(=NULL) 정리 메커니즘은 사실상 부재**.

### 1.2 Orphan 레코드 정리 로직 — **P0**

**SET_NULL로 NULL이 된 행을 의미 있게 정리하는 자동화는 없다.** 발견된 유일한 cleanup 흐름:

| 위치 | 무엇을 정리하나 | 한계 |
|------|---------------|------|
| `sec_pipeline/management/commands/rematch_unmatched.py` | `SupplyChainEvidence.target_company__isnull=True` 행 중 generic 용어 evidence 삭제 + ticker 재매칭 시도 | **수동 실행 (management command)**. 정기 배치 등록 흔적 없음 |
| `news/services/news_neo4j_sync.py:700` | Neo4j 그래프 안의 `(:NewsEvent)` orphan 노드 삭제 (관계 0개) | **Neo4j 내부만**. PG 테이블의 `news_id=NULL` 행은 무관 |

#### P0-1. orphan 검출/정리 부재로 인한 잠재 누적:
- `SupplyChainEvidence.target_company=NULL`: SET_NULL 외에도 LLM 추출 후 미매칭 케이스가 자연 누적 (`sec_pipeline.intelligence.py:92`에서 `match_unmatched` 카운팅만 함)
- `AnalysisSession.basket=NULL`: 바구니 삭제 후 세션이 무의미한 상태로 남음 → 데이터셋 재구성 불가
- `Decision.context_analysis_run=NULL`: 의사결정이 어느 분석 시점에 내려졌는지 추적 불가
- `ChatSession.analysis_run=NULL`: 대화는 보존되나 컨텍스트 손실

#### 권고 (코드 변경 없음, 운영 가이드 차원):
- **분기 cleanup 배치** 등록 검토: orphan 행을 archived 테이블로 옮기거나 retention policy 정의
- **SET_NULL FK에 `db_index=True` 추가 검토** — `__isnull=True` 필터 쿼리가 빈번하므로 (sec_pipeline에서 6회 이상)

---

## CASCADE 체인

### 2.1 CASCADE 사용 분포 — 실측 90곳 (14개 파일)

사전 파악 명령서의 "37곳, 7개 파일"은 부분 집합. 실측치:

| 영역 | CASCADE FK 수 | 비고 |
|------|--------------|------|
| portfolio/models.py | 12 | 가장 많음 (Wallet/Analysis 트리) |
| graph_analysis/models.py | 8 | watchlist + stock_a + stock_b |
| thesis/models/* | 13 | thesis/learning/community/indicator/monitoring 합산 |
| chainsight/models/* | 9 | event_reaction/insider/revenue/capital/event/sensitivity/narrative/chain_profile/saved_path |
| stocks/models.py | 6 | DailyPrice, WeeklyPrice, StockOverviewKo, EODSignal, SignalAccuracy, StockNews |
| sec_pipeline/models.py | 6 | RawDocumentStore→Evidence, BusinessModel chain |
| serverless/models.py | 4 | ScreenerAlert→AlertHistory 등 |
| rag_analysis/models.py | 5 | DataBasket→BasketItem, Session→Message |
| validation/models/* | 7 | symbol, metric, preset 트리 |
| metrics/models/* | 5 | snapshot/benchmark 트리 |
| macro/models/* | 5 | indicators/relationships |
| users/models.py | 5 | Portfolio, Watchlist, WatchlistItem, UserInterest |
| news/models.py | 2 | NewsEntity→Highlight |
| marketpulse/models/news.py | 2 | — |

### 2.2 PROTECT 사용처 (CASCADE 방어막) — 15곳

`Stock` 삭제 시 명시적으로 차단되는 곳:

| 모델 | 파일:라인 | 의미 |
|------|----------|------|
| `WalletHolding.stock` | portfolio/models.py:90 | 실 보유 데이터 보호 |
| `MetricResult.stock` | portfolio/models.py:392 | 분석 결과 보호 |
| `DiagnosticCard.target_stock` | portfolio/models.py:494 | 진단 카드 보호 |
| `LLMComment.stock` | portfolio/models.py:565 | LLM 코멘트 보호 |
| `CompanyMetricSnapshot.symbol` | metrics/models/metric_snapshot.py:11 | 지표 스냅샷 보호 |
| `ChainNewsEvent.symbol` | chainsight/models/news_event.py:23 | 뉴스 이벤트 보호 |
| `MarketPulseSectorFlow.market_index` | marketpulse/models/snapshot.py:51 | 거시 인덱스 보호 |

> **유의: 다른 도메인은 모두 `stocks.Stock`에 CASCADE — Stock 1건 삭제가 광범위 데이터 삭제 트리거**.

### 2.3 Stock 삭제 시 영향 범위 — **P1**

`Stock.symbol`(PK)을 CASCADE로 참조하는 곳 (PROTECT 제외):

```
stocks.Stock (DELETE)
├── stocks.DailyPrice                (CASCADE)
├── stocks.WeeklyPrice               (CASCADE)
├── stocks.BalanceSheet              (CASCADE)
├── stocks.IncomeStatement           (CASCADE)
├── stocks.CashFlowStatement         (CASCADE)
├── stocks.StockOverviewKo           (CASCADE, OneToOne)
├── stocks.EODSignal                 (CASCADE)
├── stocks.SignalAccuracy            (CASCADE)
├── stocks.StockNews                 (CASCADE, null=True 가능)
├── users.Portfolio                  (CASCADE) — User-Portfolio 관계도 폭파
├── users.WatchlistItem              (CASCADE)
├── users.User.favorite_stock        (M:N, 자동 제거)
├── sec_pipeline.RawDocumentStore    (CASCADE) ←── 2단계 캐스케이드 시작
│   ├── sec_pipeline.SupplyChainEvidence       (CASCADE on source_document)
│   └── sec_pipeline.BusinessModelSnapshot     (CASCADE on source_document)
│        └── sec_pipeline.BusinessModelEvidence (CASCADE on snapshot) ← 3단
├── sec_pipeline.SupplyChainEvidence (CASCADE on source_company)
├── sec_pipeline.BusinessModelSnapshot(CASCADE on symbol)
├── chainsight.CompanyChainProfile         (CASCADE, OneToOne to_field='symbol')
├── chainsight.CompanyEventReaction        (CASCADE)
├── chainsight.CompanyInsiderSignal        (CASCADE)
├── chainsight.CompanyRevenueStructure     (CASCADE)
├── chainsight.CompanyCapitalDNA           (CASCADE)
├── chainsight.CompanyGrowthStage          (CASCADE)
├── chainsight.CompanySensitivity          (CASCADE)
├── chainsight.CompanyNarrativeTag         (CASCADE)
├── graph_analysis.CorrelationEdge         (CASCADE × 2: stock_a, stock_b)
├── graph_analysis.GraphMetadata           (CASCADE on stock)
├── validation.CompanyMetricLatest         (CASCADE)
├── validation.CompanyBenchmarkDelta       (CASCADE)
├── validation.CategoryScore               (CASCADE)
├── validation.ValidationNewsSummary       (CASCADE)
├── validation.PeerPreset                  (CASCADE)
└── validation.UserPeerPreference          (CASCADE)
```

#### 3단계 이상 연쇄 삭제 경로:

1. **Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence** (4단)
2. **Stock → RawDocumentStore → SupplyChainEvidence + (target_company SET_NULL)** — `source_document` CASCADE / `target_company` SET_NULL의 비대칭
3. **User → Wallet → WalletHolding (PROTECT on stock)** — Stock 보호로 차단됨, 하지만 User 삭제는 wallet 전체 삭제
4. **User → Portfolio → AnalysisRun → {MetricResult, DiagnosticCard, LLMComment, StoredAnalysis, ChatSession→Message}** (4단, ChatSession은 SET_NULL이라 분기)
5. **User → Watchlist → CorrelationMatrix + CorrelationEdge** (3단)

#### 위험 포인트:
- **Stock 단건 삭제도 최소 30개 테이블에 영향**. 운영 중 일반 admin이 실수로 삭제 시 폭발적 데이터 손실
- **`Stock.symbol`을 PK + to_field='symbol'로 사용 → CASCADE 시 PG가 모든 자식 테이블 락 + delete**. 대용량 테이블(DailyPrice, EODSignal)일 경우 장시간 lock
- **권고**: `Stock`의 deletion 차단 (Admin override) — 현재는 PG/Django 레벨 차단 없음

---

## Neo4j 동기화

### 3.1 neo4j_dirty 플래그 채택 모델 — 3개

| 모델 | 파일 | 단일 소스 여부 |
|------|------|--------------|
| `chainsight.RelationConfidence` | chainsight/models/relation_discovery.py:130 | ✓ 단일 소스 (audit P0 #9, 2026-04-29 통일) |
| `chainsight.CompanyChainProfile` | chainsight/models/chain_profile.py:65 | ✓ 단일 소스 |
| `sec_pipeline.SupplyChainEvidence` | sec_pipeline/models.py:100 | ✓ 단일 소스 |

> **`synced_to_neo4j` 필드는 폐지됨** (DECISIONS audit P0 #9, 2026-04-29). 모든 모델이 `neo4j_dirty` + `neo4j_synced_at` 패턴으로 통일.

### 3.2 동기화 메커니즘

#### a) `chainsight.services.neo4j_sync.sync_dirty_relations()`
- `RelationConfidence.objects.filter(neo4j_dirty=True).iterator(chunk_size=100)`
- relation_status에 따라 upsert / delete 분기
- 성공 시 `queryset.update(neo4j_dirty=False)` (save() 호출 회피, dirty 재발 방지)
- 에러는 try/except로 로그만 남기고 다음 row 처리

#### b) `sec_pipeline.tasks.sync_dirty_to_neo4j` — **모범 패턴**
- **2-Phase + `select_for_update(skip_locked=True)`**:
  - Phase A: PG transaction.atomic + lock + dict 복사 (BATCH_SIZE=500)
  - Phase B: Neo4j DELETE + CREATE (dynamic type)
  - Phase C: 성공한 ID만 `neo4j_dirty=False, neo4j_synced_at=now`
- `RELATED_TO` 고정 type 사용 금지 / MERGE 금지 (코드 주석)

#### c) Celery 진입점
- `chainsight.tasks.neo4j_dirty_sync_tasks.run_neo4j_dirty_sync`: `max_retries=2, default_retry_delay=60`
- `sec_pipeline.tasks.sync_dirty_to_neo4j`: `max_retries=1, soft_time_limit=300, time_limit=360`

### 3.3 동기화 실패 시 재시도

| 메커니즘 | 위치 | 평가 |
|---------|------|------|
| Celery `max_retries` | tasks decorator | ✓ 설정됨 (2회 / 1회) |
| 개별 row 실패 격리 | `chainsight.services.neo4j_sync.py:42` | ✓ try/except per row, 다음 row 진행 |
| PG row lock으로 동시 sync 방지 | `sec_pipeline.tasks.py:367` | ✓ `select_for_update(skip_locked=True)` |
| 부분 실패 시 dirty 유지 | `chainsight.services.neo4j_sync.py:48` | ✓ `synced_pks`만 update — 실패한 row는 dirty 유지 → 재시도 |

> **재시도 메커니즘은 견고함**. PR-3 + audit P0 #9 정리 결과 양호.

### 3.4 PG ↔ Neo4j 불일치 감지 — **P0**

#### 현재 감지 가능한 것:
- `sec_pipeline.intelligence.py:97-98`: `sync_pending = filter(neo4j_dirty=True, target_company__isnull=False).count()` — **dirty 적체만**
- `sec_pipeline.quality_checks.py:90-96`: dirty 50건 초과 시 경고

#### **감지 불가능한 것 (위험)**:
1. **PG에는 행이 있고 Neo4j에는 엣지가 없는 경우**:
   - 이론적으로 `neo4j_dirty=False, neo4j_synced_at=...`인데 누군가 Neo4j에서 직접 엣지 삭제한 경우 → 영구 불일치
   - Neo4j DB 재구축 / 마이그레이션 후 PG `neo4j_dirty=False`인 행을 다시 동기화하는 메커니즘 부재
2. **PG에는 없는데 Neo4j에는 남아있는 엣지**:
   - PG SQL DELETE / 마이그레이션 / CASCADE로 RelationConfidence 삭제 시 Neo4j 엣지 정리 미발생
   - `RelationConfidence`에는 `pre_delete` 시그널이 없음 → orphan Neo4j 엣지 누적
3. **양방향 일관성 검증 배치 부재**:
   - "PG count vs Neo4j count" 같은 sanity check 없음
   - `news_neo4j_sync.py:700`이 유일한 Neo4j-side orphan cleanup (NewsEvent에만 해당)

#### 권고 (운영):
- **주기 audit task 도입 검토**:
  - PG의 `neo4j_dirty=False` 행 샘플링 → Neo4j MATCH로 엣지 존재 확인
  - Neo4j에서 PG에 없는 엣지 카운팅 (Cypher: `MATCH (a)-[r]->(b) WHERE NOT EXISTS ...`)
- **RelationConfidence/SupplyChainEvidence/CompanyChainProfile에 `pre_delete` signal** 도입 검토 — Neo4j 엣지 동기 삭제

### 3.5 save() 부수효과 — **P2**

`RelationConfidence.save()` (chainsight/models/relation_discovery.py:146-159):
```python
def save(self, *args, **kwargs):
    if self.pk:
        ...previous_status 추적...
    self.neo4j_dirty = True   # ← 무조건 True
    super().save(*args, **kwargs)
```

#### 문제:
- **`relation_status`나 score 변경이 없는 단순 필드 수정**(예: `score_version` 갱신, 메타데이터 보정)에도 `neo4j_dirty=True`로 설정 → 불필요한 Neo4j sync 트리거
- 동기화 비용 증가, 적체 감지 임계치(50건) 오발생 가능

#### 보완책 (이미 존재):
- `queryset.update()` 사용 시 save() 미호출 → dirty 미세팅 → **bulk_update 시 수동 토글 책임**이 호출자에게 있음 (`chainsight/tasks/relation_tasks.py:382-402`)
- 코드 주석에 "bulk_update에서는 save() 미호출되므로 수동 관리 필요"라고 명시 — 일관된 정책 ✓

---

## Unique 제약조건

### 4.1 unique_together / UniqueConstraint 현황

**총 53곳** (`models.py` 기준, migrations 제외)에서 unique 제약 설정. 도메인별:

| 도메인 | 모델 수 | 핵심 unique 키 |
|--------|---------|--------------|
| stocks | 7 | DailyPrice/WeeklyPrice `(stock, date)`, 재무제표 3종 `(stock, period_type, fiscal_year, fiscal_quarter)`, EODSignal `(stock, date)`, SignalAccuracy `(stock, signal_date, signal_tag)` |
| users | 4 | Portfolio/WatchlistItem `(user, stock)`, Watchlist `(user, name)`, UserInterest `(user, interest_type, value)` |
| validation | 5 | symbol/fiscal_year/metric_code/preset_key 패턴 |
| graph_analysis | 4 | `(watchlist, date)`, `(watchlist, stock_a, stock_b, date)`, `(stock, date)` |
| metrics | 3 | symbol/industry/fiscal_year/metric_code/preset_key 패턴 |
| chainsight | 5 | `(symbol_a, symbol_b)`, `(symbol_a, symbol_b, period)`, `(symbol_a, symbol_b, relation_type)`, `(source, source_id)`, `(symbol, event_type)` |
| sec_pipeline | 1 | `(alias, context_sector)` |
| serverless | 11 | mover/sector_perf/corp_action/etf_holding/theme_match/institutional 등 |
| portfolio | 5 | UniqueConstraint 명시 사용 (`unique_card_priority_per_run` 등) |
| news | 2 | `(news, symbol)`, `(symbol, date)` |
| macro | 4 | indicator-date 등 |
| marketpulse | 6 | 스냅샷 `(date, universe)` 패턴 |
| rag_analysis | 1 | `(basket, item_type, reference_id)` |
| thesis | 4 | community, keyword, indicator, monitoring |

> **PROTECT/CASCADE/unique 정책은 도메인별로 명확하게 설계됨**.

### 4.2 update_or_create 사용 vs Race Condition — **P1**

#### 호출 사용처 카운트: **173회 (83개 파일)**

#### 4.2-A. 안전한 사용 패턴 (`transaction.atomic` + `select_for_update` 또는 unique 보장):

| 사례 | 위치 | 평가 |
|------|------|------|
| `sec_pipeline.sync_dirty_to_neo4j` (Phase A) | sec_pipeline/tasks.py:362-368 | `transaction.atomic + select_for_update(skip_locked=True)` ✓ |
| `marketpulse.sync_indicators.update_or_create` | marketpulse/tasks/sync_indicators.py:85-104 | `transaction.atomic`으로 감싸짐 ✓ |

#### 4.2-B. 위험한 사용 패턴 (atomic 없음, race 가능):

UNIQUE 제약은 있으나 `transaction.atomic` 미감싸진 사례 다수:

| 호출 위치 | unique 키 | 위험도 |
|----------|----------|--------|
| `api_request/stock_service.py:254` (Stock) | symbol PK | 동일 symbol 동시 sync 시 last-write-wins (data overwrite) |
| `api_request/stock_service.py:390-581` (Daily/Weekly/BalanceSheet/Income/CashFlow) | `(stock, date)`, `(stock, period_type, fiscal_year, fiscal_quarter)` | UniqueViolation은 catch되나 동시 호출 시 `defaults` 적용 순서 불확정 |
| `validation/services/preset_generator.py:118-449` (PeerPreset, 6회) | `(symbol, preset_key)` | 동일 종목/preset 동시 생성 시 일부 update 누락 가능 |
| `serverless/services/theme_matching_service.py:247-575` (ThemeMatch, 3회) | `(stock_symbol, theme_id)` | Tier A/Tier B 동시 호출 시 evidence 덮어쓰기 |
| `serverless/services/keyword_service.py:202` (StockKeyword) | `(symbol, date)` | Celery 병렬 키워드 생성 시 결과 덮어쓰기 |
| `serverless/services/data_sync.py:196` (MarketMover) | `(date, mover_type, symbol)` | OK (unique 강함) |
| `graph_analysis/services/correlation_calculator.py:290-388` (CorrelationMatrix, GraphMetadata) | `(watchlist, date)` | OK (unique 강함) |
| `serverless/services/regulatory_service.py:480, 521` (StockRelationship, 2회) | `(source_symbol, target_symbol, relationship_type)` | atomic 없음 — 동시 enrichment 시 last-write-wins |
| `serverless/services/institutional_holdings_service.py:305, 425` | `(institution_cik, stock_symbol, report_date)` | atomic 없음 |
| `chainsight/tasks/relation_tasks.py:291` (RelationConfidence) | `(symbol_a, symbol_b, relation_type)` | `defaults` write 시 dirty flag 자동 True. 동시 sync task 시 dirty가 미세 race |
| `thesis/tasks/eod_pipeline.py:308-337` (IndicatorReading, 3회) | `(indicator, asof)` | atomic 없음 |

#### 4.2-C. Django update_or_create 내부 동작 요약:
- `_get_or_create_object()` 내부에서 1) `get()` 시도 → 2) DoesNotExist면 INSERT → 3) IntegrityError catch 시 다시 `get()` + `update()`
- **PostgreSQL 격리 수준 `READ COMMITTED`에서**: 동시 INSERT 시도가 동일 unique 키에 대해 한쪽만 성공 → 다른 쪽은 `get + update`로 폴백
- 폴백 update의 `defaults` 값이 후행 쓰기를 덮어쓰는 양상은 **last-write-wins** (Django의 의도된 동작)
- **DB 레벨 무결성은 보장**되나, **애플리케이션 의미상 race condition**(예: A의 데이터로 update 했는데 B의 후속 update가 덮어씀)은 발생

#### 권고 (코드 변경 없음, 리뷰 차원):
- **빈도 높은 batch 작업**(Celery Beat에서 매분/매시간 트리거되는 update_or_create)에 `transaction.atomic + select_for_update`나 멱등성 보강 검토
- 가장 우선 검토 대상: `api_request/stock_service.py` (코어 데이터 수집), `serverless/theme_matching_service.py` (LLM 출처 다중)

### 4.3 기타 무결성 관찰

#### P1-D. `rematch_unmatched.py:46` invalid status 값
```python
UnmatchedCompanyQueue.objects.filter(...).update(status='not_company')
```
- `UnmatchedCompanyQueue.STATUS_CHOICES` (sec_pipeline/models.py:310-317)는 `['pending', 'matched', 'not_public', 'person', 'duplicate', 'skipped']`
- `'not_company'` 값은 choices에 **없음** → CharField는 choices를 DB 제약으로 강제하지 않으므로 데이터는 들어가나, choices 기반 admin/serializer에서 표시 깨짐 가능
- **권고**: 추후 PR에서 `not_public`(가장 가까운 의미) 또는 새 choice 추가 검토

#### P2. `CompanyAlias.unique_together = (alias, context_sector)`
- `context_country` 필드는 unique 제약에서 의도적으로 제외 (`sec_pipeline/models.py:287, 294`)
- 같은 alias + 같은 sector라도 country가 다르면 충돌 발생 → 충돌 시 admin이 직접 해결해야 함 (메타데이터 참고용)

#### P3. `Stock.favorite_stock` (users/models.py:17)
```python
favorite_stock = models.ManyToManyField(Stock, max_length=100, default="", blank=True,)
```
- `ManyToManyField`에 `max_length`, `default=""` 사용 — Django에서 무시되는 인자. 의도가 명확하지 않음 (`through` 미사용)
- 로직 영향 없음 (Django가 silently ignore)

#### P3. AdminActionLog / FilingProcessLog / PipelineLog / AlertHistory unique 미설정
- 모두 감사 로그/실행 로그 모델이므로 의도적 — append-only가 자연스러움 ✓

---

## 부록 A. 모델 파일 리스트 (참조용)

```
graph_analysis/models.py
users/models.py
news/models.py
stocks/models.py
sec_pipeline/models.py
serverless/models.py
portfolio/models.py
rag_analysis/models.py

# 분할 모델 디렉토리
metrics/models/          (3 files)
chainsight/models/       (10 files)
macro/models/            (3 files)
thesis/models/           (6 files)
marketpulse/models/      (5 files)
validation/models/       (5 files)
```

## 부록 B. 핵심 무결성 패턴 인용

### B.1 RelationConfidence save() 부수효과 (chainsight/models/relation_discovery.py:146)
```python
def save(self, *args, **kwargs):
    if self.pk:
        try:
            old = RelationConfidence.objects.filter(pk=self.pk).values_list(
                'relation_status', flat=True
            ).first()
            if old and old != self.relation_status:
                self.previous_status = old
        except Exception:
            pass
    self.neo4j_dirty = True   # 무조건 True
    super().save(*args, **kwargs)
```

### B.2 SEC sync 2-Phase 모범 패턴 (sec_pipeline/tasks.py:362)
```python
with transaction.atomic():
    dirty_qs = (
        SupplyChainEvidence.objects
        .filter(neo4j_dirty=True, target_company__isnull=False)
        .select_related('source_company', 'target_company', 'source_document')
        .select_for_update(skip_locked=True)[:BATCH_SIZE]
    )
    rows = [...dict 복사...]
# Phase B: Neo4j 동기화 (PG 트랜잭션 밖)
# Phase C: 성공한 ID만 update(neo4j_dirty=False)
```

### B.3 neo4j_sync 단일 소스 정책 (chainsight/services/neo4j_sync.py:45-51)
```python
# queryset.update() 사용 — save() 호출 금지 (dirty가 다시 True로 덮어씌워짐)
# audit P0 #9: synced_to_neo4j 제거, neo4j_dirty 단일 소스
if synced_pks:
    RelationConfidence.objects.filter(pk__in=synced_pks).update(
        neo4j_dirty=False,
        neo4j_synced_at=timezone.now(),
    )
```

---

## 종합 권고 요약

1. **P0**: PG↔Neo4j 양방향 일관성 검증 배치 도입 검토 (현재 dirty 적체만 모니터링)
2. **P0**: SET_NULL orphan 행 정리 정책/배치 정의 (현재 수동 management command만 존재)
3. **P1**: `Stock` 삭제 시 영향 범위 차단 메커니즘(Admin guard, DELETE protection) 검토
4. **P1**: update_or_create 빈도 높은 핵심 sync 경로에 `transaction.atomic` 보강 검토
5. **P1**: `rematch_unmatched.py`의 `'not_company'` choice 누락 정리
6. **P2**: `RelationConfidence.save()` 부수효과 — 필드별 selective dirty 마킹 검토
7. **P3**: `Stock.favorite_stock`의 dead 인자(`max_length`, `default`) 정리
