# 데이터 무결성 감사 보고서

- **감사 일자**: 2026-04-25 (재감사, 04-24 대비 델타 반영)
- **대상**: /Users/byeongjinjeong/Desktop/stock_vis (브랜치: `portfolio`)
- **범위**: FK orphan · CASCADE 체인 · Neo4j 동기화 · Unique 제약
- **형식**: 읽기 전용 (코드 수정 없음)

## 04-24 대비 델타

| 변동 | 코드 영향 | 본 감사 영향 |
|------|-----------|--------------|
| `df85496` Alpha Vantage 전면 제거 | `api_request/alphavantage_*.py`, `news/providers/alphavantage.py`, `scripts/fetch_all_stock_data.py` 등 7개 파일 삭제 + 8개 파일 분기 정리 | Race hotspot 표에서 alphavantage_service 6곳 **삭제** (잔존 hotspot은 `api_request/stock_service.py`로 단일화) |
| `1d3386e` `timezone.now().date()` → `timezone.localdate()` 일괄 치환 (22 파일 49건) | `rag_analysis/models.py`, `news/services/*`, `serverless/*`, `chainsight/tasks/seed_tasks.py`, `macro/*`, `thesis/*`, `sec_pipeline/intelligence.py` | 모델 스키마 무변동. KST 자정~09시 구간에서 cutoff/__date 필터가 어긋나던 cross-app 데이터 무결성 결함 해소 (감사 항목 외 긍정적 변경) |

> 모델 FK/CASCADE/UniqueConstraint 정의 자체는 무변동. 04-24 발견 이슈(High 3건, Medium 5건, Low 4건)는 모두 **유효**.

---

## 요약 (위험도별 이슈 수)

| 위험도 | 건수 | 주요 내용 |
|--------|------|-----------|
| 🔴 High | 3 | `chainsight.tasks.relation_tasks.check_stale_and_decay`가 `synced_to_neo4j`만 갱신하고 `neo4j_dirty` 누락 → Neo4j 엣지 decay 미반영 / `RelationConfidence`의 이중 플래그(`synced_to_neo4j` + `neo4j_dirty`) 공존(원칙 위반) / 핫스팟 `update_or_create`(Stock/Daily·Weekly Price/재무제표/RelationConfidence/StockRelationship)에 `select_for_update` 보호 부재 |
| 🟠 Medium | 5 | Neo4j → PG 역방향 orphan edge/node 감지 잡 전무 / `NewsArticle`은 동기화 플래그 자체 부재(매 배치 Neo4j pull) / `SupplyChainEvidence.target_company=SET_NULL` 영구 orphan 정리 정책 미정의 / `InvestmentThesis.user`·`Thesis.source_news`·`ThesisIndicator.premise`·`AnalysisSession.basket`·`EconomicEvent.related_indicator`·`AnalysisRun.wallet_snapshot_at_execution` cleanup 잡 부재 / `CompanyAlias` unique_together가 `context_country` 제외로 다국가 동명기업 최초등록승리 |
| 🟡 Low | 4 | 대다수 앱이 구버전 `unique_together` 사용(표준 `UniqueConstraint` 도입은 portfolio 앱뿐) / 사용자 제공 추정치(SET_NULL 7곳/CASCADE 37곳)는 **실제보다 과소**(SET_NULL 16곳 / CASCADE 93곳) / Stock PK가 `symbol`(CharField, `to_field='symbol'`)이어서 대소문자 변환만으로도 FK 스키마 깨짐 가능 / Thesis/Watchlist/AnalysisRun/Wallet 3단 이상 CASCADE 체인이 UI 경고 없이 발동 |

> 사전 파악 수치 정정:
> - `on_delete=models.SET_NULL` 실제 **16건**(지시 7건) — `thesis`(4) + `portfolio`(3) + `serverless`(3) + `rag_analysis`(3) + `sec_pipeline`(1) + `chainsight`(1) + `macro`(1)
> - `on_delete=models.CASCADE` 실제 **93건**(지시 37건) — `portfolio`(12) + `serverless`(4) + `chainsight`(11) + `validation`(8) + `metrics`(5) + `macro`(5) + `thesis`(7) + 기타
> - 본 보고서는 실제 소스 전체 기준.

---

## FK orphan 위험

### SET_NULL 위치 (실제 앱 16곳)

| # | 파일:라인 | 모델.필드 | 참조 타입 | Orphan 정리 로직 |
|---|-----------|-----------|-----------|------------------|
| 1 | `sec_pipeline/models.py:86` | `SupplyChainEvidence.target_company` | Stock | 🟠 없음 — `TickerMatcher` 재시도 대상이지만 영영 매칭 실패한 row의 정리 정책 미정의 |
| 2 | `serverless/models.py:660` | `ScreenerAlert.preset` | ScreenerPreset | ✅ `get_effective_filters`에서 `filters_json` 폴백 — 의도된 보존 |
| 3 | `serverless/models.py:808` | `InvestmentThesis.user` | User | ❌ 탈퇴자 테제 고아 누적, 정리 잡 없음 |
| 4 | `serverless/models.py:1409` | `AdminActionLog.user` | User | ✅ 감사 로그는 의도적 보존 |
| 5 | `rag_analysis/models.py:145` | `AnalysisSession.basket` | DataBasket | ❌ 바구니 삭제 후 세션만 남아 근거 데이터 불명 |
| 6 | `rag_analysis/models.py:256` | `UsageLog.session` | AnalysisSession | ✅ 비용/토큰 보존 목적 |
| 7 | `rag_analysis/models.py:263` | `UsageLog.message` | AnalysisMessage | ✅ 동일 |
| 8 | `chainsight/models/news_event.py:54` | `ChainNewsEvent.duplicate_of` | self | ✅ 파생 이벤트 보존 |
| 9 | `macro/models/indicators.py:282` | `EconomicEvent.related_indicator` | EconomicIndicator | ❌ 지표 체계 리팩토링 시 이벤트 고립 |
| 10 | `thesis/models/thesis.py:70` | `Thesis.source_news` | NewsArticle | ❌ 30일 TTL 뉴스 삭제 후 진입 근거 추적 불가 |
| 11 | `thesis/models/thesis.py:77` | `Thesis.copied_from` | self | ✅ 원본 삭제돼도 복사본 유지 |
| 12 | `thesis/models/indicator.py:15` | `ThesisIndicator.premise` | ThesisPremise | ❌ 전제 삭제 시 지표가 근거 없이 관측 |
| 13 | `thesis/models/monitoring.py:66` | `ThesisAlert.indicator` | ThesisIndicator | ✅ 과거 알림 이력 보존 |
| 14 | `portfolio/models.py:327` | `AnalysisRun.wallet_snapshot_at_execution` | WalletSnapshot | 🟠 snapshot 삭제 후 분석은 유지되나 RV4-b 수익률 breakdown의 비교 기준 증발 — 정리 필요 |
| 15 | `portfolio/models.py:732` | `ChatSession.analysis_run` | AnalysisRun | ✅ 의도적 느슨한 연결(`portfolio/models.py:722` 주석) |
| 16 | `portfolio/models.py:831` | `Decision.context_analysis_run` | AnalysisRun | ✅ run 삭제 후에도 의사결정 이력 보존 |

> 모든 SET_NULL 필드는 `null=True` 동반 확인됨 (스키마 일관성 OK).

### Orphan 정리 잡(cleanup job) 존재 여부

- ❌ **`target_company__isnull=True` 정리 태스크 부재** (`sec_pipeline`)
  - 있는 것: 카운트 집계만 (`sec_pipeline/quality_checks.py:143`, `sec_pipeline/intelligence.py:98`)
  - `quality_checks.py:90-97`은 `neo4j_dirty + target_company__isnull=False`가 50건 초과 시 경고만 기록하고, 영구 orphan(target 매칭 실패)은 **모니터링 사각지대**
- ❌ `InvestmentThesis.user=None`, `Thesis.source_news=None`, `ThesisIndicator.premise=None`, `AnalysisSession.basket=None`, `EconomicEvent.related_indicator=None`, `AnalysisRun.wallet_snapshot_at_execution=None`을 주기적 정리하는 Celery Beat 태스크 없음
- ⚠️ SET_NULL은 "연결 단절 허용"이 아니라 "미해결 매칭 대기"로 남는 경우가 다수 — **영구 orphan 정책(삭제/보류 전환/아카이브)** 을 `DECISIONS.md`에 명문화 권장

---

## CASCADE 체인

### 주요 체인 구조 (실제 앱 93곳)

#### Stock (`stocks.Stock`) — 삭제 시 최대 영향 범위

Stock은 `symbol`(CharField) PK + 다수 FK 타깃. 직접 `delete()` 시 **모두 즉시 삭제**:

| 참조 소스 | 파일:라인 | 비고 |
|-----------|-----------|------|
| DailyPrice, WeeklyPrice | `stocks/models.py:133, 244` | `to_field='symbol'` |
| StockOverviewKo | `stocks/models.py:699` | OneToOne PK |
| EODSignal, SignalAccuracy | `stocks/models.py:756, 801` | |
| StockNews | `stocks/models.py:888` | `null=True` 허용 |
| Portfolio(legacy users), WatchlistItem | `users/models.py:28, 198` | `to_field='symbol'` |
| RawDocumentStore, SupplyChainEvidence(source), BusinessModelSnapshot | `sec_pipeline/models.py:25, 82, 161` | |
| CompanyChainProfile | `chainsight/models/chain_profile.py:12` | OneToOne PK |
| 7개 chainsight 스냅샷 (growth/capital/sensitivity/revenue/narrative/insider/event_reaction) | `chainsight/models/*.py` | 모두 CASCADE |
| CorrelationEdge(stock_a, stock_b), PriceCache | `graph_analysis/models.py:77, 84, 291` | |
| validation 전체 (BenchmarkDelta, CategoryScore, MetricLatest, NewsSummary, PeerPreset members) | `validation/models/*.py` | 5곳 |

**PROTECT 6곳 — Stock 삭제를 DB 레벨에서 차단 (portfolio/metrics/chainsight)**:

| 참조 소스 | 파일:라인 | on_delete | 평가 |
|-----------|-----------|-----------|------|
| WalletHolding.stock | `portfolio/models.py:90` | **PROTECT** | ✅ 보유 기록 불변성 보호 |
| MetricResult.stock | `portfolio/models.py:393` | **PROTECT** | ✅ 분석 결과 보호 |
| DiagnosticCard.target_stock | `portfolio/models.py:495` | **PROTECT** | ✅ 진단 카드 보호 |
| LLMComment.stock | `portfolio/models.py:566` | **PROTECT** | ✅ LLM 생성물 보호 |
| ChainNewsEvent.symbol | `chainsight/models/news_event.py:23` | **PROTECT** | ✅ 이벤트 이력 보호 |
| CompanyMetricSnapshot.stock | `metrics/models/metric_snapshot.py:11` | **PROTECT** | ✅ 메트릭 스냅샷 보호 |

> **영향도**: AAPL 1건 삭제 시 즉시 CASCADE로 연쇄되는 테이블이 **20개 이상**이지만, PROTECT 6곳이 buffer로 작동해 실제로는 **삭제 자체가 실패**(`ProtectedError`). 단, legacy 앱(`stocks/`, `users/`, `serverless/`, `graph_analysis/`, `validation/`, `sec_pipeline/`)은 여전히 CASCADE만 사용 → Stock에 직접 `delete()` 호출 경로가 있다면 PROTECT가 raise하기 전 **롤백 비용**만 발생. Stock 삭제 차단 정책이 `CLAUDE.md`/`DECISIONS.md`에 명문화돼 있지 않음.

#### User — 탈퇴 시 연쇄 삭제 체인

```
User CASCADE
├─ Portfolio(users) — legacy                                (1)
├─ Watchlist CASCADE
│  ├─ WatchlistItem                                         (2)
│  ├─ CorrelationMatrix
│  ├─ CorrelationEdge
│  │  └─ CorrelationAnomaly                                 (3)
│  └─ GraphMetadata
├─ UserInterest                                             (1)
├─ ScreenerPreset (serverless)                              (1)
├─ ScreenerAlert CASCADE
│  └─ AlertHistory                                          (2)
├─ DataBasket CASCADE
│  └─ BasketItem                                            (2)
├─ AnalysisSession CASCADE
│  └─ AnalysisMessage                                       (2)
│     (UsageLog.session/message는 SET_NULL로 비용 보존)
├─ PeerPreset / UserPeerPreference (validation)             (1)
├─ Thesis CASCADE
│  ├─ ThesisPremise
│  ├─ ThesisIndicator CASCADE
│  │  └─ IndicatorReading                                   (3)
│  └─ ThesisAlert/Comment/Vote ...
├─ SavedPath CASCADE (chainsight)
│  └─ PathAction                                            (2)
├─ Wallet CASCADE (portfolio)
│  ├─ WalletHolding   [Stock FK는 PROTECT]                  (2)
│  ├─ WalletSnapshot                                        (2)
│  └─ Portfolio CASCADE
│     └─ AnalysisRun CASCADE
│        ├─ MetricResult                                    (5)
│        ├─ DiagnosticCard                                  (5)
│        ├─ LLMComment                                      (5)
│        └─ StoredAnalysis                                  (5)
├─ ChatSession CASCADE (portfolio)
│  └─ Message                                               (3)
├─ Decision (portfolio)                                     (1)
└─ InvestmentThesis (SET_NULL — 탈퇴 후에도 보존)
```

- 🔴 **5단계 체인**: `User → Wallet → Portfolio → AnalysisRun → MetricResult/DiagnosticCard/LLMComment/StoredAnalysis`
  - `AnalysisRun.is_finalized=True` 불변성 플래그는 `save()` 수준에서만 작동 → `queryset.update()` 또는 CASCADE 삭제로 우회 가능
  - `StoredAnalysis.save_type='saved'`로 영구 저장된 분석도 상위 체인이 끊기면 휘발
- 🔴 **3단계 이상 체인 다수 잔존**:
  1. `User → Thesis → ThesisIndicator → IndicatorReading` (장기 관측 로그)
  2. `User → Watchlist → CorrelationEdge → CorrelationAnomaly` (알림 이력)
  3. `User → ChatSession → Message` (Coach 대화 raw)
- ⚠️ `Thesis`/`Watchlist`/`Wallet` 수동 삭제 시에도 동일 체인 발동 — UI에 "연쇄 삭제 영향" 경고 부재

#### RawDocumentStore (SEC 10-K 원문)

```
RawDocumentStore CASCADE
├─ SupplyChainEvidence                                      (2)
└─ BusinessModelSnapshot CASCADE
   └─ BusinessModelEvidence                                 (3)
```

- `sec_pipeline/tasks.py:120`의 `RawDocumentStore.update_or_create` 재실행 시 기존 문서 재파싱으로 하류 근거를 통째 재생성하는 **의도된 설계**
- 리스크: 실수로 `doc.delete()` 호출 시 LLM 비용(Track A+B)이 전부 휘발 — 관리 커맨드에 `--force` 가드 권장

### 3단계 이상 CASCADE 종합

| 체인 | 깊이 | 리스크 |
|------|------|--------|
| User → Wallet → Portfolio → AnalysisRun → (MetricResult/Card/LLMComment/StoredAnalysis) | **5** | portfolio 전체 분석 이력 소실 |
| User → ChatSession → Message | 3 | Coach 대화 raw |
| User → Thesis → ThesisIndicator → IndicatorReading | 4 | 관측 로그 |
| User → Watchlist → CorrelationEdge → CorrelationAnomaly | 4 | 알림 이력 |
| User → AnalysisSession → AnalysisMessage | 3 | RAG 대화 컨텍스트 |
| Stock → RawDocumentStore → BusinessModelSnapshot → BusinessModelEvidence | 4 | 10-K 품질 지표 |

> **portfolio 앱의 PROTECT 전략이 Stock 보호의 모범**이지만, User-측 CASCADE는 여전히 5단계까지. 사용자 탈퇴 플로우에 **Soft Delete + 아카이브 기간** 도입 검토 권장.

---

## Neo4j 동기화

### 플래그 패턴 혼재 현황

| 앱 | 모델 | 플래그 필드 | save() 자동 dirty | 정상 여부 |
|----|------|-------------|-------------------|-----------|
| sec_pipeline | `SupplyChainEvidence` | `neo4j_dirty` + `neo4j_synced_at` | ❌ (수동, `validator_track_a.py:158`, `ticker_matcher.py:98`) | ✅ `models.py:99` 주석: "synced_to_neo4j 필드 금지 — neo4j_dirty만" |
| chainsight | `RelationConfidence` | `neo4j_dirty` + `synced_to_neo4j` + `neo4j_synced_at` + `score_version` | ✅ (`save()` 자동, `relation_discovery.py:160`) | 🔴 **2개 플래그 공존 — 원칙 위반** |
| chainsight | `CompanyChainProfile` | `neo4j_synced`(+`_at`) | ❌ 수동 | 🟠 패턴 불일치 (`neo4j_dirty` 아님) |
| news | `NewsArticle` | **없음** | — | 🟠 `news_neo4j_sync.py:541-542` 주석 "neo4j_synced 필드가 없으므로 Neo4j에 이미 존재하는 article_id를 제외" — 매 배치 Neo4j pull 필요 |

#### 🔴 High: 이중 플래그 동기화 분열 — `chainsight.RelationConfidence`

`chainsight/models/relation_discovery.py:129-136` 두 플래그 동시 존재:

```python
synced_to_neo4j = models.BooleanField(default=False)    # legacy
neo4j_dirty = models.BooleanField(                       # standard
    default=True, db_index=True,
    help_text='True이면 Neo4j 동기화 필요. save() 시 자동 True.',
)
```

`chainsight/services/neo4j_sync.py:23`은 `neo4j_dirty=True`만 조회 후 동기화 완료 시 두 필드 동시에 갱신 (`neo4j_sync.py:48`):

```python
.update(neo4j_dirty=False, synced_to_neo4j=True, neo4j_synced_at=...)
```

**결함 — `chainsight/tasks/relation_tasks.py:389, 396, 403` `check_stale_and_decay`**:

```python
decayed += stale.update(relation_status='stale', synced_to_neo4j=False)  # ← neo4j_dirty 누락
decayed += weak.update(relation_status='weak', synced_to_neo4j=False)   # ← 동일
decayed += hidden.update(relation_status='hidden', synced_to_neo4j=False) # ← 동일
```

`queryset.update()`는 `save()` 미호출 → `save()` 내부의 `neo4j_dirty=True` 자동 세팅 안 됨 → `sync_dirty_relations`가 이 row 미수집 → Neo4j 엣지가 `confirmed` 상태로 남고 decay edge 삭제 미발동.

대조 예시 (`chainsight/tasks/sync_tasks.py:167`)는 올바르게 둘 다 세팅:
```python
).update(synced_to_neo4j=False, neo4j_dirty=True)
```

**정책 충돌**: `sec_pipeline/models.py:99`와 `CLAUDE.md` DECISIONS는 "neo4j_dirty 단일화" 원칙이지만, chainsight는 legacy 플래그 잔존으로 실구현이 어긋남.

### 동기화 실패 재시도 메커니즘

| 태스크 | 파일 | max_retries | 재시도 전략 |
|--------|------|-------------|-------------|
| `sync_dirty_to_neo4j` (SEC) | `sec_pipeline/tasks.py:337` | **2** (decorator) | soft_time_limit=300, raise 시 Celery 기본 재시도 |
| `sync_profiles_to_neo4j` | `chainsight/tasks/sync_tasks.py:96` | **1** | iterator + 건별 try/except — 실패 건은 `fail` 카운트, 다음 주기에 `neo4j_synced=False`로 재진입 |
| `sync_relations_to_neo4j` | `chainsight/tasks/sync_tasks.py:147` | **1** | `sync_dirty_relations`에 위임 |
| `run_neo4j_dirty_sync` | `chainsight/tasks/neo4j_dirty_sync_tasks.py:14` | **2** (`default_retry_delay=60`, exponential 아님) | 60초 고정 지연 |
| `sync_dirty_relations` | `chainsight/services/neo4j_sync.py:32` | (래퍼 없음) | 실패한 pk는 `synced_pks`에 미포함 → `neo4j_dirty=True` 유지 → 자동 재진입 ✅ |
| `news_neo4j_sync` | `news/services/news_neo4j_sync.py` | — | Neo4j에 존재하는 article_id 제외하는 dedupe 로직(idempotency) |

- ✅ **건별 try/except + dirty 유지** 패턴은 정상 작동
- 🔴 **Decay 결함** (위 High): dirty가 세팅 안 되어 영원히 재시도되지 않음
- ⚠️ exponential backoff 부재 — 일시적 Neo4j 장애에 60초 고정 지연으로 단순 재시도. 영속적 재시도는 "dirty 유지 + 다음 Beat 주기"에 의존
- ⚠️ `CLAUDE.md` 코딩규칙: "Celery 태스크 max_retries=3 + exponential backoff" — `chainsight/sec_pipeline` Neo4j sync 태스크는 max_retries=2 + 고정 지연으로 **규칙 미준수**

### PG ↔ Neo4j 불일치 감지 방법

#### PG → Neo4j (one-way detection, 존재)

- `sec_pipeline/quality_checks.py:91-97`: `neo4j_dirty=True AND target_company__isnull=False` > 50건 경고 로그
- `sec_pipeline/quality_checks.py:144`: dashboard에 `neo4j_synced` / `neo4j_pending` 카운트
- `sec_pipeline/intelligence.py:97-98`: `sync_synced / sync_pending` → LLM 품질 리포트 `sync_score` 입력
- `chainsight/tasks/neo4j_dirty_sync_tasks.py`: `neo4j_dirty=True` 일괄 조회 + 실패 건 dirty 유지

#### Neo4j → PG (역방향, 🟠 Medium 부재)

- **PG에 없는데 Neo4j에 있는 엣지/노드(orphan edge)를 감지하는 코드 전무**
- `sec_pipeline/tasks.py:400-412`는 `source='sec_10k'` edge를 `KNOWN_TYPES` 6개로 DELETE 시도해 동기화 전 정리하지만, 리스트 외 legacy type(예: `chainsight/tasks/sync_tasks.py:163`의 일회성 `RELATED_TO` cleanup 외)은 감지 불가
- `news_neo4j_sync.py:564`의 `_get_existing_event_ids()`는 중복 방지용이지 정합성 검증이 아님
- **대조 쿼리 cron 부재**: Neo4j에만 있는 Stock 노드/엣지를 찾아 경보하는 daily 잡 없음
- portfolio 앱은 현 단계 PG-only — Phase 2 Neo4j 편입 시 동일 패턴 재현 우려

### 기타 동기화 원칙 준수

- ✅ `sec_pipeline/tasks.py:367` `select_for_update(skip_locked=True)` — 동시 실행 안전
- ✅ Phase A/B/C 분리 패턴 — PG lock → Neo4j write → PG update (Celery 중복 실행에 강함)
- ✅ `chainsight/tasks/sync_tasks.py:159-168` 일회성 `RELATED_TO` cleanup을 cache 플래그로 멱등 보장

---

## Unique 제약조건

### unique_together / UniqueConstraint 현황

UniqueConstraint(최신 표준)는 **portfolio 앱 4곳만** 사용. 그 외 앱은 전부 구버전 `unique_together`.

| 앱 | 파일 | 종류 | 개수 | 예시 |
|----|------|------|------|------|
| stocks | `models.py` | `unique_together` | 5 | `(stock, date)` × 2, `(stock, period_type, fiscal_year, fiscal_quarter)` × 3 |
| users | `models.py` | `unique_together` | 4 | `(user, stock)`, `(user, name)`, `(watchlist, stock)`, `(user, interest_type, value)` |
| news | `models.py` | `unique_together` | 2 | `(news, symbol)`, `(symbol, date)` |
| serverless | `models.py` | `unique_together` | 9 | `(symbol, date, action_type)`, `(date, sector)`, `(institution_cik, stock_symbol, report_date)` 등 |
| graph_analysis | `models.py` | `unique_together` | 4 | `(watchlist, date)` × 2, `(watchlist, stock_a, stock_b, date)`, `(stock, date)` |
| sec_pipeline | `models.py` | `unique_together` | 1 | `(alias, context_sector)` — ⚠️ `context_country`는 모델에 있으나 unique에서 제외 (`models.py:287`) |
| thesis | `models/indicator.py` | `unique_together` | 1 | `(indicator, asof)` |
| rag_analysis | `models.py` | `unique_together` | 1 | `(basket, item_type, reference_id)` |
| metrics | `models/*` | `unique_together` | 3 | `(symbol, fiscal_year, metric_code)` × 2, `(symbol, fiscal_year, metric_code, preset_key)` |
| chainsight | `models/*` | `unique_together` | 7+ | `(symbol_a, symbol_b)`, `(symbol_a, symbol_b, period)`, `(source, source_id)`, `(symbol, event_type)` 등 |
| **portfolio** | `models.py` | **UniqueConstraint** | **4** | `(analysis_run, stock, metric_id)`, `(analysis_run, priority)`, LLMComment 동일, `(metric_id, industry_code, date)` |
| portfolio | `models.py` | `unique_together` | 1 | `(wallet, stock)` — 일부는 구버전 잔존 |

### 🔴 High: update_or_create 관련 Race Condition 방어 현황

#### 통계
- `update_or_create` 총 **150건** (test 포함). 운영 코드 핫스팟은 약 70지점
- `select_for_update` 운영 사용: **6지점** — `rag_analysis/views.py:143, 252`, `users/views.py:695, 864`, `sec_pipeline/tasks.py:367`, `serverless/tasks.py` 일부

#### Race 위험 구간 (unique key로 IntegrityError 방어는 되나 동시성 비용 발생)

| 위치 | 모델 | unique key | 트랜잭션 보호 |
|------|------|-----------|---------------|
| `api_request/stock_service.py:254` | Stock | `symbol` PK | ❌ 없음 — 동일 심볼 동시 갱신 시 last-write-wins |
| `api_request/stock_service.py:390, 417, 678` | DailyPrice/WeeklyPrice | `(stock, date)` | ❌ |
| `api_request/stock_service.py:481, 532, 581` | 재무제표 3종 (Balance/Income/CashFlow) | `(stock, period, year, quarter)` | ❌ |
| `validation/services/preset_generator.py:118~449` | PeerPreset 계열 | 복합 key | ❌ |
| `validation/services/benchmark_calculator.py:83, 238, 272, 330` | PeerListCache, Benchmark 3종 | 복합 key | ❌ |
| `news/services/aggregator.py:415, 433` | NewsEntity, EntityHighlight | `(news, symbol)` | ❌ |
| `chainsight/tasks/relation_tasks.py:275~367` (3 업소트) | RelationConfidence | `(symbol_a, symbol_b, relation_type)` | ❌ — 동일 Beat가 여러 worker에서 돌면 충돌 |
| `sec_pipeline/tasks.py:120` | RawDocumentStore | `accession_no` unique | ❌ |
| `sec_pipeline/tasks.py:314` | RelationConfidence | 동일 | ❌ |
| `serverless/services/supply_chain_service.py:328`, `regulatory_service.py:480, 521`, `patent_network_service.py:327, 379`, `institutional_holdings_service.py:425`, `news_relation_matcher.py:201` | StockRelationship | `unique_together` | ❌ |
| `serverless/services/theme_matching_service.py:247, 329, 575` | ThemeMatch | `(stock_symbol, theme_id)` | ❌ |
| `chainsight/tasks/profile_tasks.py:106, 180` 등 | 7개 프로파일 모델 | `(symbol)` / `(symbol, date)` | ❌ |
| `metrics/management/commands/seed_metric_definitions.py:518` | MetricDefinition | 커맨드 단일 실행 | ✅ 운영 동시성 없음 |

> 04-24 대비: Alpha Vantage 제거(`df85496`)로 `api_request/alphavantage_service.py:81, 235, 266, 289, 318, 347` 6개 hotspot **제거됨**. 잔존 hotspot은 `api_request/stock_service.py`로 단일화.

#### ✅ 올바르게 보호된 곳

- `sec_pipeline/tasks.py:362-368` `sync_dirty_to_neo4j` — `transaction.atomic()` + `select_for_update(skip_locked=True)` + BATCH_SIZE=500
- `rag_analysis/views.py:143, 252`, `users/views.py:695, 864` — DataBasket/Watchlist 조회 `select_for_update`

#### Race Condition 실제 영향도

- Django `update_or_create`는 내부적으로 `get → create → IntegrityError 캐치 → update 재시도` → unique key만 지키면 **데이터 무결성 유지**
- 단, 동시 호출 시:
  1. **듀얼 INSERT 경합** → IntegrityError 캐치 비용
  2. **UPDATE race**: 두 프로세스가 서로 다른 `defaults`로 같은 row를 update하면 **last write wins** (`truth_score`, `current_score`, `last_triggered_at`, `use_count` 등 손실 가능)
  3. `F()` 원자적 증가 미사용 시 카운터 누락

### NewsArticle의 동기화 플래그 부재 (🟠 Medium)

- `news_neo4j_sync.py:541-542`: "neo4j_synced 필드가 없으므로 Neo4j에 이미 존재하는 article_id를 제외"
- `_get_existing_event_ids()`가 매 배치마다 전체 이벤트 ID를 Neo4j에서 pull — **N+ 라운드트립 + Neo4j 크기 증가 시 OOM 위험**
- `neo4j_dirty` 패턴 미적용 사유는 주석에서만 파악 — `DECISIONS.md` 결정 기록 부재

### CompanyAlias의 country 제외 unique (🟠 Medium)

- `sec_pipeline/models.py:287` 주석: "context_country 필드가 모델에는 있으나 unique key에서 의도적으로 제외"
- 결과: "Samsung" 같은 다국적 회사명이 여러 국가 컨텍스트에서 추출되면 **첫 등록 승리**, 후속 국가는 무시
- 의도/버그 여부 `DECISIONS.md` 기록 부재

---

## 부록: 교차 정책 충돌

1. **`CLAUDE.md` common-bug #21**: "ETF_PEER→ETFHolding, HAS_THEME→ThemeMatch 분기" → `serverless/models.py`의 `ETFHolding`/`ThemeMatch`는 legacy 마커(`LEGACY_KEEP_UNTIL_DC2`)로 unique_together 유지. DC-2 완료 후 마이그레이션 누락 시 orphan 가능
2. **CLAUDE.md "neo4j_dirty 단일화"** vs **`RelationConfidence.synced_to_neo4j` 잔존** → 본 감사 High-1 이슈 직결
3. **portfolio 앱의 PROTECT 채택** vs **legacy 앱의 CASCADE** 혼재 — Stock 삭제 정책의 비대칭. Stock 삭제 API 운영 차단이 명문화돼 있지 않음 (`CLAUDE.md` 원칙 6은 `symbol.upper()`만 언급)
4. **portfolio `is_finalized` 불변성**은 `save()` 수준에서만 작동 — `queryset.update()`/CASCADE 삭제로 우회 가능. finalized run의 **삭제 차단**도 필요
5. **CLAUDE.md "Celery 태스크 max_retries=3 + exponential backoff"** vs **chainsight `run_neo4j_dirty_sync` max_retries=2 + 60초 고정 지연** — 규칙 미준수

---

## 권장 후속 작업 (본 감사는 코드 수정 없음)

- [HIGH-1] `chainsight/tasks/relation_tasks.py:389, 396, 403` decay update에 `neo4j_dirty=True` 추가 (별도 티켓)
- [HIGH-2] `RelationConfidence.synced_to_neo4j` 제거 마이그레이션 또는 `neo4j_dirty`와 통일 → DECISIONS 동기화
- [HIGH-3] 핫스팟 `update_or_create`(Stock/DailyPrice/WeeklyPrice/재무제표 3종/RelationConfidence/StockRelationship)에 `transaction.atomic() + select_for_update` 패턴 적용 검토
- [MED-1] Neo4j → PG 역방향 orphan edge/node 감지 daily 잡 신설
- [MED-2] SET_NULL 계열(`SupplyChainEvidence.target_company`, `InvestmentThesis.user`, `Thesis.source_news`, `ThesisIndicator.premise`, `AnalysisSession.basket`, `EconomicEvent.related_indicator`, `AnalysisRun.wallet_snapshot_at_execution`) 영구 orphan 정책 문서화 + cleanup 잡
- [MED-3] `NewsArticle`에 `neo4j_synced`/`neo4j_dirty` 추가 또는 대체 전략 DECISIONS 등재
- [MED-4] `CompanyAlias` country 제외 unique의 의도성 DECISIONS 명문화
- [MED-5] Neo4j sync Celery 태스크 재시도 정책을 `CLAUDE.md` 규칙(`max_retries=3` + exponential backoff)에 정렬
- [LOW-1] 기존 앱 `unique_together` → `UniqueConstraint` 점진적 마이그레이션 (portfolio 표준 참조)
- [LOW-2] `AnalysisRun.is_finalized=True` 인스턴스의 CASCADE 삭제 차단(`pre_delete` signal 또는 Soft Delete 전환) 검토
- [LOW-3] Stock 삭제 차단 정책을 `CLAUDE.md`/`DECISIONS.md`에 명문화 (legacy CASCADE 경로 식별 + 운영 API 가드)
